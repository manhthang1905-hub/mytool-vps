// Chỉ số kênh — thu thập analytics YouTube Studio.
//
// NGUYÊN TẮC: MỘT TAB LÀM VIỆC DUY NHẤT, đổi link lần lượt.
// Không mở/đóng tab liên tục (từng gây rò rỉ tab → Chrome hết RAM → tắt),
// không bao giờ đụng tới tab người dùng đang mở.
//
// Mỗi link: đổi URL → tải lại một lần (Studio hay hỏng khi vào thẳng link sâu)
//           → chờ dữ liệu ngừng về → sang link kế tiếp. Xong thì để tab ở about:blank.

// Để trống = lưu thẳng vào thư mục Tải xuống của máy (bản dành cho người dùng thường).
// Điền địa chỉ máy chủ nhận nếu bạn có dựng một cái.
const HOST_MAC_DINH = '';
// Mốc chụp (giờ sau đăng). 72–120h là giai đoạn YouTube quyết định có mở rộng phân phối
// hay không (video 1 bùng impressions đúng ở 72–117h) — thiếu mốc ở đó là mù đúng chỗ cần nhìn.
// ═══ MỐC CHỤP — DÀY Ở HAI NGÀY ĐẦU, VÌ MỌI QUYẾT ĐỊNH NẰM Ở ĐÓ ═══
//
// Bản cũ là [24, 48, 72, …]: KHÔNG có mốc 13h. Mà 13h chính là mốc sổ tay kênh dùng để phán
// một video sống hay chết ("so cùng mốc 13h: V1 427 · V2 469 · V3 577 ‖ V4 41 · V5 43 · V6 67").
// Mấy con số 13h đang có trong kho đều là ăn may — do lượt "chụp ngay" lúc phát hiện video mới
// rơi trúng, hoặc do chụp tay. Đo 05/09/2026: cả 6 video, không video nào có mốc 13h do lịch đặt.
//
// Thêm 6h (thấy đường khởi động), 13h (cửa thử đầu tiên), 18h, 30h (luật 30 giờ của sổ tay),
// 36h. Hai ngày đầu thành 8 mốc thay vì 2. Mỗi lượt chụp ~1 phút và không tốn tiền API.
const MOC_DAY = [6, 13, 18, 24, 30, 36, 48, 72, 96, 120];

// ═══ MỐC HẰNG NGÀY QUA NGÀY 5, TỚI 30 NGÀY (29/09/2026) ═══
//
// Bản cũ dừng dày ở 120h rồi nhảy thẳng 168h (7 ngày) → 336h (14 ngày) → 672h (28 ngày):
// hai khe hở 7 và 14 ngày KHÔNG có mốc nào. Vòng học (`core/vong_hoc.py`) cần số liệu MỖI
// NGÀY của mọi video còn trong 30 ngày gần đây (`core/ho_so_video.doc_bang_hieu_suat_tieu_de`
// dùng cửa sổ này chấm tiêu đề theo CTR) — khe hở nhiều ngày là đúng lỗi "[vòng học] số liệu
// Studio cũ" dai dẳng dù tiện ích vẫn đang chạy (log thật 29/09: TL1-T7-0001 đứng ở số liệu
// 94 giờ trước).
//
// Từ ngày 6 (144h) tới ngày 30 (720h): MỖI 24 GIỜ một mốc, KHÔNG còn khe hở. Mốc mới dùng
// chụp NHẸ (`nhe = true`, xem `chupVideo`) — chỉ một link (tab tổng quan, không xuất CSV) —
// vài giây thay vì gần một phút, để 20+ mốc thêm một tháng không đụng trần thời gian phiên
// (`vm/agent.py: CHO_QUET_GIAY`, ~8 phút/kênh). Ngày 0–5 GIỮ NGUYÊN chụp ĐẦY (4 link, có CSV
// nguồn/vùng) — không đổi hành vi của giai đoạn quyết định sớm.
const MOC_NGAY_NHE = [];
for (let ngay = 6; ngay <= 30; ngay++) MOC_NGAY_NHE.push(ngay * 24);
const MOC = MOC_DAY.concat(MOC_NGAY_NHE);
//: Mốc lớn hơn ngần này dùng chụp NHẸ (chỉ tab tổng quan) thay vì đủ 4 link.
const NGUONG_NHE_GIO = 120;
const laNhe = (gio) => Number(gio) > NGUONG_NHE_GIO;
const captures = {};          // tabId -> {maLink, count, last, so, card, coSo}
const lanTay = {};            // "videoId|endpoint" -> lần ghi cuối từ tab người dùng (chống rác)
let nhanHienTai = null;       // {videoId, label, maLink} của link đang mở trong lượt chụp
let tabLamViec = null;
let soGoi = 0;                // số thứ tự gói (tên tệp không trùng)
let logs = [];
let endpoints = {};
let giuThuc = null;
const TRANG_NGHI = chrome.runtime.getURL('nghi.html');

// ---------------------------------------------------------------- tiện ích
const cho = (ms) => new Promise(r => setTimeout(r, ms));
const pad = (n) => String(n).padStart(2, '0');
const stamp = (d = new Date()) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
const log = (m) => { logs.unshift(`${new Date().toLocaleTimeString()} ${m}`); logs = logs.slice(0, 200); chrome.storage.local.set({ logs }); };
const st = async (k, mac = {}) => (await chrome.storage.local.get(k))[k] ?? mac;
const luu = (k, v) => chrome.storage.local.set({ [k]: v });
const b64 = (s) => btoa(unescape(encodeURIComponent(s)));

// service worker MV3 hay bị ngủ giữa chừng → giữ thức trong lúc làm việc
const batGiuThuc = () => { if (!giuThuc) giuThuc = setInterval(() => chrome.runtime.getPlatformInfo(() => {}), 20000); };
const tatGiuThuc = () => { if (giuThuc) { clearInterval(giuThuc); giuThuc = null; } };

// ═══ MỌI LỜI GỌI TRONG LƯỢT CHỤP ĐỀU CÓ HẠN (12/10/2026) ═══
//
// TL2-T7 11/10: lượt chụp cuối xong lúc 03:22:07, rồi tiện ích IM 21 phút tới hết giờ chờ của
// agent — không lượt nào chạy tiếp, không chụp kênh, không "quét xong". Một lời gọi không bao
// giờ trả (`executeScript` chờ trang "idle", `fetch` về trạm không trả lời…) là đủ giữ tab cả
// lượt. Từ nay lời gọi nào quá hạn thì ném lỗi, nơi gọi đi tiếp.
const coHan = (p, ms, ten) => Promise.race([p, new Promise((_, loi) =>
  setTimeout(() => loi(new Error(`quá ${Math.round(ms / 1000)} giây chờ ${ten}`)), ms))]);
async function fetchCoHan(url, tuy = {}, ms = 20000) {
  const ac = new AbortController();
  const hen = setTimeout(() => ac.abort(), ms);
  try { return await fetch(url, Object.assign({}, tuy, { signal: ac.signal })); }
  finally { clearTimeout(hen); }
}

// ═══ KHOÁ TAB THẬT — MỘT VIỆC MỘT LÚC (12/10/2026) ═══
//
// Bản cũ giữ tab bằng cờ `dangChay` + vòng `while (dangChay) await cho(3000)`, rồi `await
// st('daChup')` TRƯỚC khi bật cờ. Báo thức quá hạn của mọi video đều đặt "nổ sau 2 giây" trong
// cùng một vòng (`datLich`) nên mọi lượt chờ thức dậy CÙNG PHA — cả chục lượt cùng lọt khe
// `await` ấy, và lượt nào xong trước cũng hạ cờ hộ lượt khác. Đo thật:
//   · TL2 11/10 03:20:13–03:21:05: 15 video chụp CÙNG LÚC trên MỘT tab → quota ảnh
//     (MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND), đọc chữ trúng `nghi.html` (lượt khác vừa đưa
//     tab về trang nghỉ), 15 lượt "HỎNG", gói của video này rơi vào nhãn của video kia.
//   · TL1 12/10 02:42:09: 12 lượt nhẹ cùng mở; cả 12 "xong 6 gói" bằng ĐÚNG 6 gói của
//     vidGiaad6bc → `daChup` ghi vidGia685d6 142h là đã có số, thư mục thật thì rỗng.
// Nay: một hàng đợi có ưu tiên (khám phá > kênh > video ≤ 5 ngày > video cũ, cùng mức thì tới
// trước làm trước). Mỗi lượt cầm một MÃ; chỉ người cầm mã mới nhả được. Người cầm treo quá
// `HAN_GIU_TAB_MS` thì người kế lấy lại (nhịp `hoi-lenh` mỗi phút gọi `moiTab`), không chết im.
const hangTab = [];           // [{uuTien, so, viec, nhan}]
let chuTab = null;            // {ma, viec, tu}
let soMaTab = 0;
const HAN_GIU_TAB_MS = 12 * 60 * 1000;
const tabBan = () => !!chuTab || hangTab.length > 0 || soViecCho > 0;
const conGiuTab = (ma) => !!chuTab && chuTab.ma === ma;
function xinTab(viec, uuTien = 0) {
  return new Promise((nhan) => {
    hangTab.push({ uuTien, so: ++soMaTab, viec, nhan });
    moiTab();
  });
}
function moiTab() {
  if (chuTab && Date.now() - chuTab.tu > HAN_GIU_TAB_MS) {
    log(`khoá tab bị "${chuTab.viec}" giữ quá ${Math.round(HAN_GIU_TAB_MS / 60000)} phút — lấy lại cho việc kế`);
    chuTab = null;
  }
  if (chuTab || !hangTab.length) return;
  let i = 0;
  for (let j = 1; j < hangTab.length; j++) if (hangTab[j].uuTien > hangTab[i].uuTien) i = j;
  const x = hangTab.splice(i, 1)[0];
  chuTab = { ma: x.so, viec: x.viec, tu: Date.now() };
  batGiuThuc();
  x.nhan(x.so);
}
function nhaTab(ma) {
  if (!chuTab || chuTab.ma !== ma) return;      // nhả hộ người khác = không làm gì
  chuTab = null;
  if (!hangTab.length && !ltDoi) tatGiuThuc();
  moiTab();
}

// ═══ CỔNG QUÉT — CHỈ QUÉT KHI TOOL MỞ CHROME CHO VIỆC "QUÉT NGÀY" (30/09/2026) ═══
//
// Chủ kênh: "vừa đăng video mới vừa quét". Trước đây mỗi lần agent mở Chrome kênh — để đăng,
// tải bổ sung, ghim bình luận — tiện ích tự chạy hết chùm báo thức quá hạn (chụp kênh, chụp
// video, khám phá) NGAY TRONG LÚC máy đăng đang lái Studio. Nay mỗi kênh có đúng MỘT việc
// QUÉT NGÀY (vm/agent.py: `chay_quet_ngay`, khung 02:10–04:00 giờ VPS), và tiện ích chỉ quét
// trong cửa sổ đó.
//
// Tín hiệu là tệp `che-do.json` do agent ghi vào CHÍNH thư mục tiện ích ngay trước khi mở
// Chrome (và ghi lại khi xong): `{"che_do": "phien", "quet_den": <ms>, "ma": "<mã lượt>"}`.
// Tiện ích chưa đóng gói đọc tệp của mình thẳng từ đĩa mỗi lần `fetch`, nên agent đổi cờ là
// có hiệu lực ngay, không cần nạp lại. KHÔNG có tệp (máy một kênh nếp cũ giữ Chrome 24/7,
// bản gửi khách) hoặc `che_do != "phien"` → quét tự do như trước — không đổi hành vi nơi khác.
async function docCheDo() {
  try {
    const r = await fetch(chrome.runtime.getURL('che-do.json') + '?t=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) return null;
    const c = await r.json();
    return (c && typeof c === 'object') ? c : null;
  } catch (e) { return null; }
}
async function choPhepQuet() {
  const c = await docCheDo();
  if (!c || c.che_do !== 'phien') return true;
  return Date.now() < Number(c.quet_den || 0);
}
let daBaoChan = false;
const baoChan = (vi_sao) => { if (!daBaoChan) { daBaoChan = true; log(`KHÔNG quét (${vi_sao}): Chrome mở cho việc đăng/bình luận — chỉ QUÉT NGÀY mới quét`); } };

const NHIEU = /log_event|\/att\/|\/ars\/|feedback|notification|get_survey|google_hats|security\/|promotions|communications|check_creator_bulk|generate_204|ptracking|\/api\/stats|play\.google|gstatic|fonts\./;
const tenEp = (u) => { try { const x = new URL(u); return (x.host.replace('studio.youtube.com', '') + x.pathname.replace('/youtubei/v1/', '')).replace(/^\//, '').slice(0, 80); } catch (e) { return u.slice(0, 80); } };
const ghiEp = (path, luuDuoc) => { const e = (endpoints[path] = endpoints[path] || { thay: 0, luu: 0 }); luuDuoc ? e.luu++ : e.thay++; chrome.storage.local.set({ endpoints }); };
chrome.webRequest.onCompleted.addListener((d) => { if (!NHIEU.test(d.url)) ghiEp(tenEp(d.url), false); },
  { urls: ['<all_urls>'], types: ['xmlhttprequest'] });

// ---------------------------------------------------------------- tab làm việc (chỉ MỘT)
// Chỉ dùng lại tab nếu nó đúng là tab làm việc của mình (about:blank hoặc Studio).
// Sau khi Chrome khởi động lại, id tab được cấp lại từ đầu nên id cũ có thể trỏ vào tab khác
// của người dùng — điều hướng nhầm sẽ cướp tab đang xem.
async function tabHopLe(id) {
  try {
    const t = await chrome.tabs.get(id);
    const u = t.url || t.pendingUrl || '';
    return u === 'about:blank' || u.startsWith(TRANG_NGHI) || u.startsWith('https://studio.youtube.com/');
  } catch (e) { return false; }
}

// Đóng tab, nhưng KHÔNG BAO GIỜ đóng tab cuối cùng của cửa sổ (đóng nó = Chrome thoát).
async function dongAnToan(id) {
  try {
    const t = await chrome.tabs.get(id);
    const cung = await chrome.tabs.query({ windowId: t.windowId });
    if (cung.length <= 1) { try { await chrome.tabs.update(id, { url: TRANG_NGHI }); } catch (e) {} return; }
    await chrome.tabs.remove(id);
  } catch (e) {}
}

// Tab làm việc được neo theo TRANG NGHỈ (url), không theo id — id đổi khi Chrome/service worker khởi động lại.
// Đồng thời dọn tab analytics còn kẹt từ lượt trước (chỉ tab KHÔNG ai đang xem).
async function layTab() {
  if (tabLamViec != null && await tabHopLe(tabLamViec)) return tabLamViec;
  // Service worker MV3 ngủ giữa chừng làm mất biến nhớ. Đọc lại id đã ghi xuống đĩa trước khi
  // nghĩ tới chuyện mở tab mới — nếu không, mỗi lần worker ngủ lại đẻ thêm một tab Studio.
  const daLuu = await st('tab_lam_viec', null);
  if (daLuu != null && await tabHopLe(daLuu)) { tabLamViec = daLuu; return daLuu; }
  try {
    const nghiTabs = await chrome.tabs.query({ url: TRANG_NGHI + '*' });
    if (nghiTabs.length) {
      await datTab(nghiTabs[0].id);
      for (const t of nghiTabs.slice(1)) await dongAnToan(t.id);
      return tabLamViec;
    }
  } catch (e) {}
  try {
    // Bắt MỌI tab Studio đang nền, không chỉ analytics/*: lượt bị ngắt giữa chừng để tab kẹt
    // ở /videos/upload, và truy vấn cũ không khớp nên tab đó nằm lại vĩnh viễn.
    const ket = await chrome.tabs.query({ url: 'https://studio.youtube.com/*', active: false });
    if (ket.length) {
      await datTab(ket[0].id);
      for (const t of ket.slice(1)) await dongAnToan(t.id);
      if (ket.length > 1) log(`gộp ${ket.length} tab Studio kẹt về 1`);
      return tabLamViec;
    }
  } catch (e) {}
  const t = await chrome.tabs.create({ url: TRANG_NGHI, active: false });
  await datTab(t.id);
  return t.id;
}

async function datTab(id) {
  tabLamViec = id;
  await luu('tab_lam_viec', id);
}

// Đổi link MỘT lần rồi chờ tới khi gói CHỈ SỐ về.
//
// ═══ VÌ SAO PHẢI PHÂN BIỆT GÓI, KHÔNG ĐẾM CHUNG ═══
//
// Bản cũ chỉ đếm `count` — MỌI gói đều tính. Nhưng mỗi trang Studio bắn ít nhất hai loại:
// `creator/get_creator_videos` (danh sách video ở thanh bên, KHÔNG có chỉ số nào) về trước,
// rồi `yta_web/get_screen` và `get_cards` (chỗ chứa chỉ số thật) về sau vài giây.
//
// Vòng chờ thoát khi "có gói + im 4 giây". Gói danh sách về lúc :20, gói chỉ số lẽ ra về lúc
// :26 — nhưng :24 là đã im đủ 4 giây nên ta đóng trang và đi tiếp. Mất trắng.
//
// Đo trên dữ liệu thật của kênh, 12 mốc tự động của video 1:
//   mốc 159h TỐT : :20 danh sách · :20 get_screen · :23 get_cards   (đều lọt cửa sổ 4 giây)
//   mốc 139h HỎNG: get_screen về, get_cards KHÔNG  → chỉ có 3 chỉ số mặc định, thiếu impressions
//   mốc 168h HỎNG: CHỈ có gói danh sách            → tệp tổng quan rỗng hoàn toàn
// Hai mốc hỏng đều ghi `impressions=None`. Tỉ lệ hỏng 2/12.
//
// `can` nói gói nào mới là đủ: 'card' cho trang tổng quan (chỉ `get_cards` mới mang bộ chỉ số ta
// đặt trong CHI_SO — `get_screen` chỉ có ba chỉ số mặc định của YouTube), 'so' cho bảng chi tiết.
//
// 12/10/2026: mỗi lần mở link mang một MÃ (`maLink`); `luuCapture` chỉ đếm gói của ĐÚNG mã ấy và
// ĐÚNG video ấy. Trước đây đếm theo tab: gói của video khác (lượt chồng, gói về trễ của trang
// trước) cũng làm vòng chờ tưởng "đủ", và lượt chụp được chấm "xong" bằng số của video khác.
// `coSo` = số gói mang CHỈ SỐ THẬT (xem `coSoVideo`/`coSoKenh`), không chỉ "có gói về".
let soLink = 0;
async function moLink(tabId, url, nhan, can = null) {
  const maLink = ++soLink;
  nhanHienTai = nhan ? Object.assign({}, nhan, { maLink }) : null;
  captures[tabId] = { maLink, count: 0, last: 0, so: 0, card: 0, coSo: 0 };
  try { await coHan(chrome.tabs.update(tabId, { url, active: true }), 15000, 'đổi trang'); }
  catch (e) { log(`không mở được trang (${e.message})`); return { tong: 0, card: 0, so: 0, coSo: 0 }; }
  const batDau = Date.now();
  let daTaiLai = false;
  const du = (c) => (can === 'card' ? c.card > 0 : can === 'so' ? c.so > 0 : c.count > 0);
  while (Date.now() - batDau < 45000) {
    await cho(500);
    const c = captures[tabId] || { count: 0, last: 0, so: 0, card: 0 };
    if (du(c) && Date.now() - c.last > 4000) break;      // đã có thứ cần + ngừng về → xong
    if (!daTaiLai && !du(c) && Date.now() - batDau > 12000) {
      daTaiLai = true;                                    // vẫn thiếu → tải lại đúng 1 lần
      log(`chưa thấy gói ${can || 'nào'} → tải lại`);
      try { await coHan(chrome.tabs.reload(tabId, { bypassCache: true }), 15000, 'tải lại'); } catch (e) {}
    }
  }
  const c = captures[tabId] || { count: 0, so: 0, card: 0, coSo: 0 };
  if (can && !du(c)) log(`THIẾU gói ${can} sau 45 giây (${c.count} gói khác)`);
  return { tong: c.count || 0, card: c.card || 0, so: c.so || 0, coSo: c.coSo || 0 };
}

// Bấm nút "Xuất → .csv" của chính Studio (mọi ngôn ngữ đều có chữ .csv).
async function xuatCSV(tabId) {
  try {
    const r = await coHan(chrome.scripting.executeScript({ target: { tabId }, func: async () => {
      const cho = (ms) => new Promise(r => setTimeout(r, ms));
      const moiNode = () => { const ra = []; const sau = (root) => { for (const e of root.querySelectorAll('*')) { ra.push(e); if (e.shadowRoot) sau(e.shadowRoot); } }; sau(document); return ra; };
      const btn = moiNode().find(e => e.id === 'export-button');
      if (!btn) return 'không thấy nút xuất';
      btn.click();
      // Menu của Studio mở CHẬM hơn 1,2 giây (đo trực tiếp: 1,2s chưa có gì, 2s đã đủ 9 mục),
      // nên chờ một khoảng cứng rồi bỏ cuộc là hỏng — nhật ký đầy "không thấy mục csv" trong khi
      // menu vẫn mở ra bình thường ngay sau đó. Chờ tới khi menu thật sự hiện.
      // Mục cần bấm mang tên đầy đủ theo ngôn ngữ giao diện, ví dụ tiếng Việt:
      // "Giá trị được phân tách bằng dấu phẩy (.csv)" — mọi ngôn ngữ đều có phần "(.csv)".
      let csv = null;
      for (let i = 0; i < 20 && !csv; i++) {
        await cho(500);
        const items = moiNode().filter(e => (e.tagName === 'TP-YT-PAPER-ITEM' || e.getAttribute('role') === 'menuitem') && e.offsetParent !== null);
        csv = items.find(e => /\.csv/i.test(e.innerText || ''));
      }
      if (!csv) { document.body.click(); return 'không thấy mục csv'; }
      csv.click(); return 'đã bấm csv';
    } }), 30000, 'bấm xuất csv');
    return r && r[0] && r[0].result;
  } catch (e) { return 'lỗi: ' + e.message; }
}

// ---------------------------------------------------------------- nhận capture
function duyet(o, f) { if (o && typeof o === 'object') { f(o); for (const k in o) duyet(o[k], f); } }

async function nhanDienVideo(res, ep) {
  // CHỈ nhận video của kênh mình: trang "chế độ nâng cao" cũng tra tiêu đề video NGUỒN ĐỀ XUẤT
  // (kênh người khác) — nhận nhầm sẽ mở analytics video không sở hữu và Studio báo lỗi.
  const kenh = await st('kenh', '');
  const tuDanhSach = /list_creator_videos/.test(ep || '');
  const videos = await st('videos', {});
  const cuaMinh = new Set();
  let moi = 0;
  duyet(res, (d) => {
    const id = d.videoId;
    if (typeof id !== 'string' || !/^[\w-]{11}$/.test(id)) return;
    // Giờ ĐĂNG thắng giờ TẠO (12/10/2026): gói nào chỉ mang `timeCreatedSeconds` (lúc tải lên —
    // sớm hơn giờ đăng 3–21 giờ với video hẹn lịch) KHÔNG được đè giờ đăng đã biết, nếu không
    // tuổi video lật qua lại giữa hai mốc và nhãn bản chụp lệch theo.
    const tsDang = Number(d.timePublishedSeconds || d.publishedTimestamp || 0);
    const tsTao = Number(d.timeCreatedSeconds || 0);
    if (!tsDang && !tsTao) return;
    const ch = d.channelId || (d.metadata && d.metadata.channelId) || '';
    if (kenh ? ch !== kenh : !(tuDanhSach && !ch)) return;
    cuaMinh.add(id);
    const v = videos[id] || {};
    if (!videos[id]) moi++;
    const giuDang = !tsDang && v.nguon_ngay === 'dang' && v.ngay_dang_ms;
    videos[id] = {
      tieu_de: d.title || v.tieu_de || '',
      ngay_dang_ms: tsDang ? tsDang * 1000 : (giuDang ? v.ngay_dang_ms : tsTao * 1000),
      nguon_ngay: (tsDang || giuDang) ? 'dang' : 'tao',
      dai_giay: Number(d.lengthSeconds || v.dai_giay || 0),
      kenh: ch || kenh,
      phat_hien: v.phat_hien || Date.now(),
    };
  });
  if (kenh && tuDanhSach && cuaMinh.size) {
    for (const id of Object.keys(videos)) {
      if (!cuaMinh.has(id)) {
        delete videos[id];
        await chrome.alarms.clear(`ngay|${id}`);
        await chrome.alarms.clear(`bu|${id}`);
        for (const h of MOC) await chrome.alarms.clear(`snap|${id}|${h}`);
        log(`bỏ video lạ ${id}`);
      }
    }
  }
  await luu('videos', videos);
  if (moi) { log(`thấy ${moi} video mới (tổng ${Object.keys(videos).length})`); await datLich(); }
}

// ═══ GÓI NÀY CÓ CHỈ SỐ THẬT KHÔNG (12/10/2026) ═══
//
// "Có gói về" KHÔNG phải "có số": Studio hay trả `get_cards`/`join` mà thẻ chỉ số rỗng, và bản
// chụp như thế từng được chấm "xong" (rồi `daChup` khoá luôn mốc đó). Hai hàm dưới khớp đúng
// điều kiện bộ giải mã phía tool (`core/chi_so_ytb/giai_ma.py: sinh`, `tong_tu_join`) dùng để
// điền `impressions`/`views` — nên "tiện ích nói có số" = "tool đọc ra số".
function coSoThe(res, cacChiSo) {
  let co = false;
  duyet(res, (d) => {
    const pc = d.primaryContent;
    if (!co && pc && typeof pc === 'object' && cacChiSo.includes(String(pc.metric || ''))
        && typeof pc.total === 'number') co = true;
  });
  return co;
}
function coSoJoin(req, res) {
  const nodes = (req && req.nodes) || [];
  for (const x of (res && res.results) || []) {
    const key = String((x && x.key) || '');
    if (!/TOTALS_SUMS/.test(key)) continue;
    // Tổng của trang pool đề xuất bị lọc YT_RELATED — chỉ là phần Đề xuất, không phải tổng video.
    const node = nodes.find((n) => n && n.key === key);
    const rs = node ? ((((node.value || {}).query) || {}).restricts || []) : [];
    if (!rs.every((r) => (((r && r.dimension) || {}).type) === 'VIDEO')) continue;
    const rt = ((x.value || {}).resultTable) || {};
    if (rt.dimensionColumns && rt.dimensionColumns.length) continue;
    const so = {};
    for (const c of rt.metricColumns || []) {
      const t = String(((c && c.metric) || {}).type || '');
      const o = c.counts || c.percentages || c.milliseconds || {};
      const v = Array.isArray(o.values) ? o.values[0] : null;
      if (t && typeof v === 'number' && !(c.undefinedValueIndices || []).length) so[t] = v;
    }
    if (typeof so.VIDEO_THUMBNAIL_IMPRESSIONS === 'number'
        && ((so.VIDEO_THUMBNAIL_IMPRESSIONS || 0) > 0 || (so.EXTERNAL_VIEWS || 0) > 0)) return true;
  }
  return false;
}
function coSoVideo(req, res, ep) {
  if (/get_cards|get_screen/.test(ep)) return coSoThe(res, ['VIDEO_THUMBNAIL_IMPRESSIONS']);
  if (/join/.test(ep)) return coSoJoin(req, res);
  return false;
}
const coSoKenh = (res, ep) => /get_cards|get_screen/.test(ep)
  && coSoThe(res, ['EXTERNAL_VIEWS', 'EXTERNAL_WATCH_TIME', 'SUBSCRIBERS_NET_CHANGE']);

async function luuCapture(msg, sender) {
  // Lấy nhãn lượt chụp NGAY khi gói tới, TRƯỚC mọi `await` (12/10/2026). Bản cũ đọc
  // `nhanHienTai` sau vài lượt `await st(...)` — lúc ấy lượt kế đã đổi nhãn, nên gói về trễ của
  // trang trước rơi vào nhãn của lượt sau: vidGiaa9179 có thư mục "23h" (nhãn của video mới
  // chụp kế đó) lúc nó đã 125 giờ tuổi; cùng một bộ số nằm ở 106h/118h/119h.
  // Và gói chỉ được nhận là của lượt chụp khi nó là của ĐÚNG video lượt ấy đang chụp.
  const nhan = nhanHienTai;
  const tabId = sender.tab && sender.tab.id;
  const vid = (msg.href.match(/\/video\/([\w-]{11})\//) || [])[1] || 'kenh';
  const laLuotChup = !!nhan && tabId === tabLamViec && nhan.videoId === vid;
  const ch = (msg.href.match(/\/channel\/(UC[\w-]+)/) || [])[1];
  if (ch) { const cu = await st('kenh', ''); if (cu !== ch) { await luu('kenh', ch); log(`kênh: ${ch}`); } }
  const kenh = (await st('ma_kenh', '')) || (await st('kenh', '')) || 'kenh';
  const tab = (msg.href.match(/\/(tab-[a-z_]+)/) || [])[1] || 'tab';
  const ep = tenEp(msg.url).replace(/[^\w.-]+/g, '-').replace(/^-|-$/g, '') || 'ep';
  const lb = laLuotChup ? nhan.label : `tay-${stamp().slice(0, 8)}`;

  // Tab Studio người dùng để mở vẫn tự gọi lại API (thẻ "Hoạt động mới nhất" làm mới mỗi 10 giây).
  // Không chặn hẳn — bản chụp tình cờ đó từng là nguồn số duy nhất của một mốc — nhưng mỗi
  // (video, endpoint) chỉ giữ 1 lần / 5 phút, nếu không một tab mở qua đêm sinh hàng trăm MB rác.
  if (!laLuotChup) {
    const k = `${vid}|${ep}`;
    if (Date.now() - (lanTay[k] || 0) < 300000) return;
    lanTay[k] = Date.now();
  }

  let req = null, res = null;
  try { req = msg.reqBody ? JSON.parse(msg.reqBody) : null; } catch (e) {}
  try { res = JSON.parse(msg.resText); } catch (e) { res = { _raw: msg.resText }; }
  if (/creator_videos|get_video/.test(ep)) nhanDienVideo(res, ep).catch(() => {});
  // Cổng quét: tab Studio của MÁY ĐĂNG (không phải lượt chụp của mình) vẫn gọi API — ngoài
  // cửa sổ QUÉT NGÀY thì không lưu/gửi gói nào (chỉ giữ việc nhận diện video ở trên, cục bộ).
  if (!laLuotChup && !(await choPhepQuet())) { baoChan('gói từ tab Studio'); return; }

  // Đếm cho vòng chờ của `moLink` — CHỈ gói của đúng link đang mở (cùng `maLink`, cùng video).
  // Đếm riêng: `so` = gói có chỉ số, `card` = gói mang đúng bộ chỉ số ta đặt trong CHI_SO,
  // `coSo` = gói mang CHỈ SỐ THẬT. `get_creator_videos` / `list_creator_videos` chỉ là danh sách.
  const c = captures[tabId];
  if (laLuotChup && c && c.maLink === nhan.maLink) {
    c.count += 1; c.last = Date.now();
    if (/get_screen|get_cards|join|csv_export/.test(ep)) c.so += 1;
    if (/get_cards/.test(ep)) c.card += 1;
    try { if (vid === 'kenh' ? coSoKenh(res, ep) : coSoVideo(req, res, ep)) c.coSo += 1; } catch (e) {}
  }
  const ten = `${stamp()}_${tab}_${ep}_${++soGoi}.json`;
  const goi = { captured_at: new Date().toISOString(), href: msg.href, url: msg.url, request: req, response: res };
  await luuGoi(kenh, vid, lb, ten, goi, msg.resText.length);
  ghiEp(tenEp(msg.url), true);
}

// Lưu một gói: có địa chỉ máy chủ thì gửi về đó, không thì ghi thẳng vào thư mục Tải xuống.
// Bản dành cho người dùng thường KHÔNG cấu hình máy chủ — extension Chrome chỉ được phép ghi
// vào Tải xuống, nên đó là chỗ dữ liệu nằm, và công cụ sẽ đọc từ đúng chỗ ấy.
async function luuGoi(kenh, vid, nhan, ten, goi, cỡ = 0, im = false) {
  const host = await st('host', '');
  if (host) {
    try {
      const r = await fetchCoHan(host + '/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kenh, id: vid, label: nhan, ten, goi }) }, 30000);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      if (!im) log(`→host ${vid}/${nhan} ${ten.slice(0, 28)} (${Math.round(cỡ / 1024)} KB)`);
      return true;
    } catch (e) { log(`máy chủ lỗi (${e.message}) → lưu vào Tải xuống`); }
  }
  try {
    const thu_muc = await st('thu_muc', 'chi-so-youtube');
    await coHan(chrome.downloads.download({ url: 'data:application/json;base64,' + b64(JSON.stringify(goi)),
      filename: `${thu_muc}/${kenh}/${vid}/${nhan}/${ten}`, conflictAction: 'uniquify', saveAs: false }), 20000, 'lưu tệp');
    if (!im) log(`↓ đã lưu ${vid}/${nhan} (${Math.round(cỡ / 1024)} KB)`);
    return true;
  } catch (e) { log(`LỖI lưu: ${e.message}`); return false; }
}

// ---------------------------------------------------------------- các lượt chụp
// Từ 24/08/2026 YouTube đếm một lượt xem CÔNG KHAI ngay từ khung hình đầu, không cần xem
// tối thiểu bao lâu. Chỉ số cũ đổi tên thành ENGAGED_VIEWS và VẪN LÀ THỨ TÍNH TIỀN cùng
// điều kiện bật kiếm tiền. Đo trên kênh thật ngày 28/08: video mới có 176 lượt công khai
// nhưng chỉ 97 lượt thật — 55%. Thiếu ENGAGED_VIEWS là mọi tỷ lệ tính từ lượt xem đều lệch
// gần gấp đôi. (AVERAGE_WATCH_TIME của Studio vốn đã tính trên lượt thật, không phải công khai.)
const CHI_SO = 't_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR&t_metrics=EXTERNAL_VIEWS&t_metrics=ENGAGED_VIEWS&t_metrics=AVERAGE_WATCH_TIME&t_metrics=EXTERNAL_WATCH_TIME';
const kho = (id, chieu, them = '') =>
  `https://studio.youtube.com/video/${id}/analytics/tab-reach_viewers/period-default/explore?entity_type=VIDEO&entity_id=${id}${them}&time_period=lifetime&explore_type=TABLE_AND_CHART&metric=EXTERNAL_VIEWS&granularity=DAY&${CHI_SO}&dimension=${chieu}&o_column=VIDEO_THUMBNAIL_IMPRESSIONS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC`;
// Sắp theo IMPRESSIONS, không phải views. Bảng tải dần khi cuộn và Xuất→.csv chỉ lấy phần đã tải,
// nên thứ tự quyết định phần nào lọt vào file. Sắp theo views thì phần đầu là mấy chục nguồn có
// view, còn impressions lại nằm rải ở hàng trăm nguồn 0-view phía sau: video 2 xuất ra 40 nguồn
// mà chỉ phủ 5,7% tổng impressions. Sắp theo impressions thì dù chỉ lấy được phần đầu, đó cũng
// là phần chiếm nhiều impressions nhất — độ phủ cao nhất có thể với cùng số dòng.

// [link, có xuất CSV, gói bắt buộc phải về, tên ảnh chụp màn hình]
const LINK_VIDEO = (id) => [
  [`https://studio.youtube.com/video/${id}/analytics/tab-overview/period-since_publish`, false, 'card', 'tong-quan'],
  [kho(id, 'TRAFFIC_SOURCE_DETAIL', '&ddr_dimension=TRAFFIC_SOURCE_TYPE&ddr_value=YT_RELATED'), true, 'so', 'pool-de-xuat'],
  // Hiển thị + CTR theo TỪNG LOẠI bề mặt (Trang chủ · Tiếp theo · Tìm kiếm…). Trước đây chỉ có
  // hai thứ rời nhau: TỔNG hiển thị của video, và SỐ LƯỢT theo bề mặt — không có hiển thị theo
  // bề mặt, nên không trả lời được câu quan trọng nhất của cổng 1: "bề mặt nào đang đói suất, và
  // ở bề mặt nào thì ảnh bìa thắng?". Đo 05/09/2026: V3 có 519 lượt "Tiếp theo" / 361 lượt
  // "Trang chủ", V4 ngược hẳn (11 / 824) — hai kiểu sóng khác nhau mà không cách nào so CTR.
  [kho(id, 'TRAFFIC_SOURCE_TYPE'), true, 'so', 'nguon-theo-loai'],
  [kho(id, 'COUNTRY'), true, 'so', 'vung'],
];

async function nghi(tabId) {
  nhanHienTai = null;
  try { await coHan(chrome.tabs.update(tabId, { url: TRANG_NGHI, active: false }), 15000, 'về trang nghỉ'); } catch (e) {}
}

// ═══ ẢNH CHỤP MÀN HÌNH TỪNG TAB SỐ LIỆU ═══
//
// Chủ dự án, 05/09/2026: *"mày có thể yêu cầu extension chụp ảnh ở các tab dữ liệu để nếu nó
// lỗi mày cũng biết"*. Đúng chỗ đau: gói JSON về đủ KHÔNG có nghĩa là số đúng. Ngày 05/09 tìm
// ra bốn lỗi mà mọi gói vẫn về đều đặn — lấy nhầm thẻ, dán nhãn thẻ này lên số thẻ kia. Không
// có gì đối chiếu được với thứ MẮT NGƯỜI nhìn thấy trên trang.
//
// Ảnh còn bắt được cả loại hỏng mà gói JSON không bao giờ kể: phiên đăng xuất, Studio đổi giao
// diện, hộp thoại chắn ngang, trang trắng. Lúc đó gói vẫn về (rỗng hoặc thiếu) và nhật ký chỉ
// ghi "THIẾU gói" — không nói vì sao.
//
// JPEG chất lượng 55: mỗi ảnh ~60–120 KB. Bốn lượt/ngày × 6 video × 4 tab ≈ 10 MB/ngày, và
// trạm nhận dọn bớt (giữ 10 mốc mới nhất mỗi video).
// Đọc CHỮ đang hiện trên trang. Đây là lưới an toàn thật, ảnh chỉ là thứ dễ nhìn:
//   · chạy được cả khi màn hình không vẽ (phiên RDP ngắt, cửa sổ thu nhỏ) — lúc ấy ảnh chụp
//     hỏng hoặc ra khung đen, còn chữ vẫn đọc được;
//   · MÁY so được. Lỗi ngày 05/09 là giải mã nhầm thẻ: số trong tệp khác số trên trang. Muốn
//     bắt kiểu lỗi ấy thì phải có con số Studio HIỂN THỊ, không phải bức ảnh để người soi.
// Studio dựng bằng web component nên `document.body.innerText` bỏ sót phần trong shadow DOM —
// phải tự đi xuống từng shadowRoot, đúng cách `xuatCSV` đang làm.
async function docChu(tabId) {
  try {
    const r = await coHan(chrome.scripting.executeScript({ target: { tabId }, func: () => {
      // Chỉ lấy chữ ĐANG HIỆN. Bản đầu lấy cả nút ẩn, và hậu quả không phải là rác thừa:
      // Studio giữ sẵn khuôn "Rất tiếc, đã xảy ra lỗi. / Thử lại" ẩn trong DOM ở MỌI trang,
      // nên bản chụp nào cũng có câu ấy. Một lưới an toàn kêu oan mỗi lượt còn tệ hơn không có
      // lưới — phiên sau sẽ học cách bỏ qua nó, đúng lúc nó kêu thật.
      // (Đối chiếu ảnh chụp cùng lượt 05/09/2026: không trang nào có banner lỗi.)
      const BO = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'HEAD', 'TITLE']);
      const hien = (e) => {
        if (e.hasAttribute && e.hasAttribute('hidden')) return false;
        if (e.offsetParent === null && e.getClientRects && e.getClientRects().length === 0) return false;
        return true;
      };
      const ra = [];
      const sau = (root) => {
        for (const e of root.querySelectorAll('*')) {
          if (BO.has(e.tagName)) continue;
          if (!hien(e)) continue;
          if (e.shadowRoot) { sau(e.shadowRoot); continue; }
          if (e.querySelector && e.querySelector('*')) continue;   // chỉ lấy lá
          const t = (e.innerText || e.textContent || '').trim();
          if (t && t.length <= 120) ra.push(t);
        }
      };
      sau(document);
      const goc = [];
      const da = new Set();
      for (const t of ra) { if (!da.has(t)) { da.add(t); goc.push(t); } }
      return (document.title + '\n' + location.href + '\n\n' + goc.join('\n')).slice(0, 20000);
    } }), 15000, 'đọc chữ trang');
    return (r && r[0] && r[0].result) || '';
  } catch (e) { return 'LỖI đọc chữ: ' + (e.message || e); }
}

// ═══ ẢNH CÓ NHỊP (12/10/2026) ═══ Chrome chỉ cho `captureVisibleTab` khoảng 2 lần/giây. Ảnh của
// các lượt chồng nhau từng ăn lỗi "MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND" hàng loạt. Khoá tab
// đã hết chồng lượt; đây là lớp thứ hai: giãn ≥ 1,1 giây giữa hai lần chụp, quá quota thì chờ
// rồi thử lại tối đa hai lần, và lời gọi nào cũng có hạn.
const KHOANG_CHUP_ANH_MS = 1100;
let lanChupAnhCuoi = 0;
async function captureVisibleTabCoNhip(windowId) {
  for (let lan = 0; ; lan++) {
    const doi = KHOANG_CHUP_ANH_MS - (Date.now() - lanChupAnhCuoi);
    if (doi > 0) await cho(doi);
    lanChupAnhCuoi = Date.now();
    try {
      return await coHan(chrome.tabs.captureVisibleTab(windowId, { format: 'jpeg', quality: 55 }), 15000, 'chụp ảnh');
    } catch (e) {
      if (lan < 2 && /MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND/.test(String(e && e.message))) { await cho(1500 * (lan + 1)); continue; }
      throw e;
    }
  }
}

async function chupAnh(tabId, kenh, vid, nhan, ten) {
  if (!ten) return false;
  const tenTep = `${stamp()}_${ten}`;
  // Tab không còn ở Studio (về trang nghỉ, bị điều hướng) thì đừng chụp/đọc trang LẠ rồi gắn nhãn
  // của video này — ghi rõ lý do thay vì "Cannot access … nghi.html".
  let tab = null;
  try { tab = await coHan(chrome.tabs.get(tabId), 5000, 'đọc tab'); } catch (e) {}
  const oStudio = !!tab && String(tab.url || '').startsWith('https://studio.youtube.com/');
  const chu = oStudio ? await docChu(tabId) : '';
  let anh = '', loi = oStudio ? '' : `tab không ở trang Studio (${String((tab && tab.url) || '?').slice(0, 80)})`;
  try {
    if (oStudio) {
      const url = await captureVisibleTabCoNhip(tab.windowId);
      anh = (url || '').split(',')[1] || '';
      if (!anh) loi = 'chụp về rỗng';
    }
  } catch (e) {
    loi = e.message || String(e);
    log(`ảnh hỏng (${ten}): ${loi}`);
  }
  const host = await st('host', '');
  if (host) {
    try {
      const r = await fetchCoHan(host + '/anh', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kenh, id: vid, label: nhan, ten: tenTep, anh, chu, loi }) }, 30000);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return true;
    } catch (e) { log(`gửi ảnh hỏng (${ten}): ${e.message}`); return false; }
  }
  const thu_muc = await st('thu_muc', 'chi-so-youtube');
  const duong = `${thu_muc}/${kenh}/${vid}/${nhan}/anh/`;
  try {
    if (anh) await chrome.downloads.download({ url: 'data:image/jpeg;base64,' + anh,
      filename: duong + tenTep + '.jpg', conflictAction: 'uniquify', saveAs: false });
    await chrome.downloads.download({ url: 'data:text/plain;base64,' + b64(chu || loi || '(rỗng)'),
      filename: duong + tenTep + '.txt', conflictAction: 'uniquify', saveAs: false });
    return true;
  } catch (e) { log(`LỖI lưu ảnh: ${e.message}`); return false; }
}

// ═══ NGÀY KÊNH BẮT ĐẦU LÀM NỘI DUNG — KHÔNG CHỤP VIDEO ĐỜI TRƯỚC ═══
//
// Bốn kênh đang chạy đều là kênh YouTube CÓ SẴN đổi sang làm tâm lý Nhật, trên kênh còn nguyên
// video của đời trước. Mắt cào này không biết video nào do tool làm nên chụp TẤT CẢ — mỗi video
// một lượt gần một phút, và số liệu ấy rồi bị bộ lọc phía tool
// (`core/chi_so_ytb/loc_video.py`) bỏ đi hết. Tức là cào xong để đấy.
//
// Mốc `ngay_bat_dau` đi xuống bằng hai đường, cả hai đều tự: `cau-hinh.json` (thư mục tiện ích,
// sống sót qua mọi lần cài lại) và câu trả lời `/lenh-tien-ich` mà tiện ích vốn hỏi mỗi phút —
// nên đổi ô "Ngày bắt đầu làm nội dung" trên tool là mắt cào biết trong một phút.
//
// KHÔNG có mốc → chụp hết, y như trước. Đây là điều kiện để bản gửi khách và mọi kênh chưa khai
// mốc không đổi hành vi một li.
async function mocMs() {
  const chu = String(await st('ngay_bat_dau', '') || '').slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(chu)) return 0;
  const t = Date.parse(chu + 'T00:00:00Z');
  return Number.isFinite(t) ? t : 0;
}

//: Video này nằm ngoài phạm vi kênh chưa. `moc = 0` → không bao giờ ngoài.
//: Video KHÔNG biết ngày đăng thì coi là TRONG phạm vi — ngược chiều với bộ lọc phía tool, và cố
//: ý: ở đây cái giá của "đoán sai" là chụp thừa một lượt (tool lọc sau), còn ở kia là rác đi vào
//: bộ chấm. Chụp thừa rồi bỏ thì mất một phút; bỏ sót thì mất số liệu của video thật.
function ngoaiPhamVi(v, moc) {
  return !!(moc && v && v.ngay_dang_ms && v.ngay_dang_ms < moc);
}

// ═══ SỔ CỦA LƯỢT QUÉT (12/10/2026) ═══
//
// Mỗi lượt QUÉT NGÀY (mã trong `che-do.json`; không có tệp thì theo ngày) giữ: số LẦN đã thử
// chụp từng video, và video nào ĐÃ có số trong lượt. Hai việc:
//   · chặn "bão thử lại": `datLich` chạy mỗi phút (nhịp `hoi-lenh`) và trước đây đặt lại báo
//     thức "nổ ngay" cho MỌI mốc còn thiếu của MỌI video hỏng — 25 phút một lượt quét thành hàng
//     trăm lượt chụp chồng nhau (TL2-T7 06/10: 394 ảnh cho một mốc của vidGia8f905);
//   · danh sách chụp bù của trạm và báo thức mốc không chụp trùng một video đã có số trong lượt.
const TOI_DA_LUOT_THU_VIDEO = 2;      // mỗi lượt quét: tối đa 2 lần xếp hàng / video (mỗi lần tự thử 3 lượt)
const NGHI_THU_LAI_MS = [15000, 45000];  // chưa có số → nghỉ 15 giây, rồi 45 giây, thử lại
const HONG_LIEN_TIEP_NGAT = 3;         // cầu dao: ngần này video liền nhau không ra số → thôi thử lại
let hongLienTiep = 0;
const dangXepVideo = new Set();        // video đang chờ / đang chụp — không xếp hàng lần hai
async function soLuot() {
  const c = await docCheDo();
  const ma = String((c && c.ma) || '') || `ngay-${stamp().slice(0, 8)}`;
  const s = await st('luot_chup', {});
  return (s && s.ma === ma) ? s : { ma, thu: {}, ok: {} };
}
async function ghiSoLuot(videoId, loai) {
  const s = await soLuot();
  if (loai === 'thu') s.thu[videoId] = (s.thu[videoId] || 0) + 1;
  else s.ok[videoId] = Date.now();
  await luu('luot_chup', s);
}

// ═══ CHỤP MỘT VIDEO ═══
//
// `mocDuDinh`: mốc báo thức định chụp ("96h"), hoặc null (chụp bù / chụp tay). `tuy`:
//   · `ep`   — bỏ qua `daChup` (lệnh tay, danh sách chụp bù của trạm);
//   · `tay`  — người bấm: không tính trần lượt thử;
//   · `bu`   — chụp bù của trạm: thôi nếu video đã có số trong lượt này.
//
// NHÃN = TUỔI THẬT lúc bắt đầu chụp (12/10/2026), không bao giờ là nhãn dự định của báo thức:
// báo thức nổ trễ là chuyện thường (Chrome chỉ mở mỗi ngày một lần), và thư mục "142h" thật ra
// chụp lúc 94h (vidGia685d6) là thứ đã làm vòng học chấm sai. `_thong-tin.json` ghi đủ: giờ
// chụp thật, tuổi thật (lẻ), mốc dự định, hợp lệ hay không.
//
// `soViecCho` đếm ĐỒNG BỘ ngay lúc gọi (trước mọi `await`): lượt vừa được gọi mà chưa kịp xếp
// hàng tab cũng tính là "còn việc", để `kiemXongQuet` không báo xong giữa chừng.
let soViecCho = 0;
async function chupVideo(videoId, mocDuDinh = null, tuy = {}) {
  soViecCho++;
  try { return await chupVideoThat(videoId, mocDuDinh, tuy); } finally { soViecCho--; }
}
async function chupVideoThat(videoId, mocDuDinh, tuy) {
  const ep = !!tuy.ep;
  const kenh = await st('kenh', '');
  let v = (await st('videos', {}))[videoId];
  // Cổng đặt ở ĐÂY chứ không chỉ ở `datLich()`: mọi đường chụp một video đều đi qua hàm này —
  // báo thức theo lịch, "Chụp ngay tất cả" của popup, và lệnh ép từ trạm. Chặn một chỗ là chặn
  // cả ba, kể cả lệnh ép: "chụp lại tất cả" nghĩa là tất cả video CỦA ĐỜI NÀY của kênh.
  const moc = await mocMs();
  if (ngoaiPhamVi(v, moc)) {
    log(`bỏ ${videoId}: đăng ${new Date(v.ngay_dang_ms).toISOString().slice(0, 10)}, trước ngày kênh bắt đầu`);
    return 0;
  }
  if (!v || (kenh && v.kenh && v.kenh !== kenh)) {
    log(`bỏ ${videoId}: không thuộc kênh`);
    const videos = await st('videos', {}); delete videos[videoId]; await luu('videos', videos);
    return 0;
  }
  // Đã chụp mốc nào thì thôi mốc đó (mốc báo thức), trừ khi bị ép chụp lại.
  const daCoMoc = async () => !ep && !!mocDuDinh && ((await st('daChup', {}))[videoId] || []).includes(mocDuDinh);
  // Báo thức bù / danh sách bù: video đã có số trong lượt này thì thôi (lượt ấy đã gộp mọi mốc đã qua).
  const daCoTrongLuot = async () => (!mocDuDinh && (!ep || tuy.bu)) && !!(await soLuot()).ok[videoId];
  if (await daCoMoc()) { log(`bỏ qua ${videoId} [${mocDuDinh}]: đã chụp mốc này rồi`); return 0; }
  if (await daCoTrongLuot()) { log(`bỏ qua ${videoId}: đã có số trong lượt quét này`); return 0; }
  if (!tuy.tay && ((await soLuot()).thu[videoId] || 0) >= TOI_DA_LUOT_THU_VIDEO) {
    log(`bỏ qua ${videoId}: đã thử ${TOI_DA_LUOT_THU_VIDEO} lần trong lượt quét này — lượt sau chụp lại`);
    return 0;
  }
  // Kiểm + ghi LIỀN NHAU, không `await` ở giữa — hai báo thức cùng video không cùng lọt.
  if (dangXepVideo.has(videoId)) { log(`bỏ qua ${videoId}${mocDuDinh ? ` [${mocDuDinh}]` : ''}: đang xếp hàng chụp rồi`); return 0; }
  dangXepVideo.add(videoId);
  const tuoiXep = v.ngay_dang_ms ? (Date.now() - v.ngay_dang_ms) / 36e5 : null;
  const ma = await xinTab(`chụp ${videoId}`, tuoiXep != null && tuoiXep <= NGUONG_NHE_GIO ? 1 : 0);
  try {
    // Xét lại SAU khi tới lượt: chùm báo thức của cùng một video xếp hàng nhau — lượt đầu chụp
    // xong đã đánh dấu các mốc đã qua, các lượt sau phải thôi, không chụp lại y hệt.
    if (await daCoMoc()) { log(`bỏ qua ${videoId} [${mocDuDinh}]: vừa chụp trong lượt này`); return 0; }
    if (await daCoTrongLuot()) { log(`bỏ qua ${videoId}: vừa có số trong lượt này`); return 0; }
    v = (await st('videos', {}))[videoId] || v;
    const batDau = Date.now();
    const tuoi = v.ngay_dang_ms ? (batDau - v.ngay_dang_ms) / 36e5 : null;
    const label = tuoi != null ? `${Math.round(tuoi)}h` : (mocDuDinh || `tay-${stamp().slice(0, 8)}`);
    const nhe = laNhe(tuoi != null ? tuoi : parseInt(mocDuDinh || '0', 10));
    const tabId = await layTab();
    log(`chụp ${videoId} [${label}]${nhe ? ' (nhẹ)' : ''}`
      + (mocDuDinh && mocDuDinh !== label ? ` — mốc ${mocDuDinh} tới lúc video đã ${label}, lưu theo tuổi thật` : ''));
    await ghiSoLuot(videoId, 'thu');
    const maKenh = (await st('ma_kenh', '')) || kenh || 'kenh';
    let tong = 0, coSo = false, lan = 1;
    // Mốc HẰNG NGÀY qua ngày 5 (`NGUONG_NHE_GIO`, xem khai báo `MOC_NGAY_NHE`) chỉ cần link
    // ĐẦU (tab tổng quan) — đó là link DUY NHẤT có đủ impressions/CTR/views/AVD (bộ giải mã
    // `core/chi_so_ytb/giai_ma.py: sinh()` đọc cả bốn số này từ `keyMetricCardData` của link
    // này). Ba link còn lại (pool đề xuất, nguồn theo loại, vùng) đều XUẤT CSV — chờ menu +
    // tải trang chiếm phần lớn thời gian của một lượt chụp ĐẦY (~1 phút). Cắt xuống một link
    // còn vài giây, để 20+ mốc thêm một tháng không đụng trần phiên (`CHO_QUET_GIAY` phía
    // `vm/agent.py`, ~8 phút/kênh) — nguồn traffic/vùng của những mốc này đành bỏ trống, đúng
    // như GHI-CHU/task cho phép ("nguồn traffic nếu có").
    const danhSachLink = nhe ? LINK_VIDEO(videoId).slice(0, 1) : LINK_VIDEO(videoId);
    for (const [url, canCSV, can, tenAnh] of danhSachLink) {
      if (!conGiuTab(ma)) break;
      const r = await moLink(tabId, url, { videoId, label }, can);
      tong += r.tong;
      if (r.coSo) coSo = true;
      if (canCSV) { log(`xuất csv: ${await xuatCSV(tabId)}`); await cho(4000); }
      // Chụp SAU khi số liệu đã về và bảng đã vẽ xong — chụp sớm chỉ ra khung xám.
      await chupAnh(tabId, maKenh, videoId, label, tenAnh);
    }
    // ═══ CHƯA CÓ SỐ → THỬ LẠI NGAY TRONG LƯỢT, GIÃN DẦN (12/10/2026) ═══
    // Trang tổng quan trước, rồi trang nguồn theo loại (gói `join` của nó mang số TỔNG của video
    // — `giai_ma.tong_tu_join`). Không xuất CSV ở lượt thử lại: chỉ cần số.
    // Cầu dao: `HONG_LIEN_TIEP_NGAT` video liền nhau không ra số thì nhiều khả năng Studio hỏng
    // cả phiên (đăng xuất, trang lỗi) — thôi thử lại từng video, để kịp lượt cho video còn lại.
    const linkThuLai = [LINK_VIDEO(videoId)[0], LINK_VIDEO(videoId)[2]];
    if (!coSo && hongLienTiep >= HONG_LIEN_TIEP_NGAT) log(`bỏ thử lại ${videoId}: ${hongLienTiep} video liền nhau không ra số — Studio có thể đang hỏng cả phiên`);
    while (!coSo && hongLienTiep < HONG_LIEN_TIEP_NGAT && lan <= NGHI_THU_LAI_MS.length && conGiuTab(ma)) {
      const nghiMs = NGHI_THU_LAI_MS[lan - 1];
      lan++;
      log(`chưa có số của ${videoId} [${label}] — nghỉ ${Math.round(nghiMs / 1000)} giây rồi thử lại (lần ${lan})`);
      await nghi(tabId);
      await cho(nghiMs);
      for (const [url, , can, tenAnh] of linkThuLai) {
        if (!conGiuTab(ma)) break;
        const r = await moLink(tabId, url, { videoId, label }, can);
        tong += r.tong;
        if (r.coSo) coSo = true;
        await chupAnh(tabId, maKenh, videoId, label, `${tenAnh}-lan${lan}`);
        if (coSo) break;
      }
    }
    await nghi(tabId);
    const xongLuc = Date.now();
    const lyDo = coSo ? '' : (conGiuTab(ma) ? `không có gói chỉ số sau ${lan} lần thử`
      : 'mất khoá tab giữa chừng (lượt treo quá hạn)');
    const cheDo = await docCheDo();
    const xong = { kenh: maKenh, id: videoId, label,
      tieu_de: v.tieu_de || '', thoi_luong: v.dai_giay || null,
      gio: tuoi != null ? Math.round(tuoi) : null,
      ngay_dang: v.ngay_dang_ms ? new Date(v.ngay_dang_ms).toISOString() : null,
      // Giờ chụp THẬT và tuổi THẬT — không suy từ tên thư mục.
      chup_luc: new Date(batDau).toISOString(), xong_luc: new Date(xongLuc).toISOString(),
      tuoi_gio_that: tuoi != null ? Math.round(tuoi * 100) / 100 : null,
      moc_du_dinh: mocDuDinh || null,
      // Bản chụp KHÔNG có số thì nói thẳng là không hợp lệ — bộ đọc bỏ qua, lượt sau chụp lại.
      hop_le: coSo, ly_do: lyDo, so_lan_thu: lan, so_goi: tong, nhe,
      luot_quet: String((cheDo && cheDo.ma) || ''), phien_ban: chrome.runtime.getManifest().version };
    const host = await st('host', '');
    if (host) {
      try {
        await fetchCoHan(host + '/done', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(xong) }, 20000);
      } catch (e) { log(`không gửi được thông tin bản chụp ${videoId}/${label} (${e.message})`); }
    } else {
      // Không có máy chủ nhận: mấy thông tin này (tiêu đề, thời lượng, mốc giờ) không nằm
      // trong gói nào của Studio, nên phải ghi thành một tệp riêng — thiếu nó thì bản chụp
      // vẫn đọc được nhưng không biết là của video nào, dài bao nhiêu, ở mốc mấy giờ.
      await luuGoi(xong.kenh, videoId, label, '_thong-tin.json', xong, 0, true);
    }
    // ═══ CHỈ ĐÁNH DẤU ĐÃ CHỤP KHI THẬT SỰ CÓ CHỈ SỐ ═══
    //
    // Bản cũ ghi vào `daChup` vô điều kiện, kể cả lượt về tay không. Mốc đó vĩnh viễn không bao
    // giờ được chụp lại — mốc 139h và 168h của video 1 nằm đó rỗng suốt, và không có cách nào
    // lấy lại vì Studio chỉ giữ chuỗi theo giờ trong một cửa sổ ngắn.
    // 12/10/2026: "có chỉ số" = gói CỦA ĐÚNG video này mang số thật (`coSoVideo`), không phải
    // "có gói get_cards nào đó về tab" — xem `moLink`.
    //
    // Thà chụp lại thừa một lượt còn hơn mất hẳn một mốc.
    if (!coSo) {
      if (conGiuTab(ma)) hongLienTiep++;
      log(`HỎNG ${videoId} [${label}]: ${lyDo} — bản chụp ghi KHÔNG HỢP LỆ, để lần chạy sau chụp lại`);
      return tong;
    }
    hongLienTiep = 0;
    const daChup = await st('daChup', {});
    const ds = (daChup[videoId] = daChup[videoId] || []);
    if (!ds.includes(label)) ds.push(label);
    if (mocDuDinh && !ds.includes(mocDuDinh)) ds.push(mocDuDinh);
    // GỘP CÁC MỐC ĐÃ QUA (30/09/2026): Chrome chỉ mở mỗi ngày MỘT lần để quét, nên một bản
    // chụp lúc video 31 giờ tuổi là số mới nhất cho MỌI mốc ≤ 31h còn thiếu (13h, 18h, 24h,
    // 30h). Chụp lại từng mốc chỉ ra cùng một bộ số, tốn ~1 phút mỗi lượt. Công cụ đọc tuổi
    // THẬT từ `captured_at` (`core/chi_so_ytb/gom.py: tuoi_that_gio`), không tin nhãn.
    const gio = tuoi != null ? Math.round(tuoi) : null;
    if (gio != null) {
      let gop = 0;
      for (const h of MOC) {
        if (h <= gio + 3 && !ds.includes(`${h}h`)) { ds.push(`${h}h`); gop++; }
      }
      if (gop) log(`gộp ${gop} mốc đã qua của ${videoId} vào bản chụp ${gio}h`);
    }
    await luu('daChup', daChup);
    await ghiSoLuot(videoId, 'ok');
    log(`xong ${videoId} [${label}]: ${tong} gói${lan > 1 ? ` (sau ${lan} lần thử)` : ''}`);
    return tong;
  } finally {
    dangXepVideo.delete(videoId);
    nhaTab(ma);
    setTimeout(() => { kiemXongQuet().catch(() => {}); }, 5000);
  }
}

// ═══ SỐ TOÀN KÊNH (12/10/2026) ═══
//
// TL2-T7 không có `kenh-<ngày>` nào từ 07/10 tới 11/10 trong khi mọi lượt quét vẫn "xong". Hai
// đường hỏng, cùng gốc là lượt chụp CHỒNG nhau (xem khoá tab): (1) chụp kênh chờ cờ `dangChay` hạ,
// mà bão chụp chồng giữ cờ suốt rồi một lượt treo giữ nốt tới hết giờ (TL2 11/10: im từ 03:22);
// (2) chụp kênh có chạy nhưng lượt video chạy chồng gọi `nghi()` xoá nhãn giữa chừng → gói kênh
// rơi vào `tay-<ngày>` (lọc trùng 5 phút bỏ gần hết; TL2 12/10 03:11: gói `tab-build_audience`
// nằm ở `tay-20261012`), trong khi dấu ngày vẫn ghi "đã chụp" sau khi đi đủ ba trang.
// Nay: kênh xếp hàng ƯU TIÊN trên mọi video, và dấu ngày (`kenh_ngay_cuoi`)
// CHỈ ghi khi có gói mang chỉ số toàn kênh — không có thì thử lại (tối đa
// `TOI_DA_THU_KENH_LUOT` lần mỗi lượt quét; lượt quét sau trong ngày — agent tự xếp khi thiếu
// `kenh-<ngày>` — lại được thử), không còn "đi đủ ba trang là xong".
const TOI_DA_THU_KENH_LUOT = 3;
async function lanThuKenh() {
  const s = await st('kenh_thu', {});
  return (s && s.ma === (await soLuot()).ma) ? (s.lan || 0) : 0;
}
let kenhDangXep = false;
let daBaoChuaBietKenh = false;
async function chupKenh(tuy = {}) {
  const ch = await st('kenh', '');
  if (!ch) {
    if (!daBaoChuaBietKenh) { daBaoChuaBietKenh = true; log('chưa biết mã kênh (UC…) — chưa chụp được số toàn kênh, lượt khám phá sẽ nhận diện'); }
    return;
  }
  const homNay = stamp().slice(0, 8);
  if (!tuy.tay && (await st('kenh_ngay_cuoi', '')) === homNay) return;
  if (kenhDangXep) return;
  kenhDangXep = true;
  const ma = await xinTab('chụp kênh', 2);
  try {
    if (!tuy.tay && (await st('kenh_ngay_cuoi', '')) === homNay) return;
    const lanNay = (await lanThuKenh()) + 1;
    await luu('kenh_thu', { ma: (await soLuot()).ma, lan: lanNay });
    const tabId = await layTab();
    const label = `kenh-${homNay}`;
    const maKenh = (await st('ma_kenh', '')) || ch || 'kenh';
    log(`chụp kênh ${ch}${lanNay > 1 ? ` (lần ${lanNay} trong lượt quét)` : ''}`);
    let coSo = 0;
    for (const tab of ['tab-overview', 'tab-content', 'tab-build_audience']) {
      if (!conGiuTab(ma)) break;
      const r = await moLink(tabId, `https://studio.youtube.com/channel/${ch}/analytics/${tab}/period-default`, { videoId: 'kenh', label }, 'so');
      coSo += r.coSo;
      await chupAnh(tabId, maKenh, 'kenh', label, tab.replace('tab-', ''));
    }
    if (!coSo && conGiuTab(ma)) {
      log('số toàn kênh chưa về — nghỉ 20 giây rồi mở lại trang tổng quan kênh');
      await nghi(tabId);
      await cho(20000);
      const r = await moLink(tabId, `https://studio.youtube.com/channel/${ch}/analytics/tab-overview/period-default`, { videoId: 'kenh', label }, 'so');
      coSo += r.coSo;
      await chupAnh(tabId, maKenh, 'kenh', label, 'overview-lan2');
    }
    // Dấu ngày CHỈ ghi khi đã có số toàn kênh. Lần Chrome mở lại trong cùng ngày sẽ không chụp
    // kênh lần hai; ngày mới thì `datLich()` nhìn thấy dấu cũ và cho chạy ngay.
    if (coSo) await luu('kenh_ngay_cuoi', homNay);
    else log(`HỎNG số toàn kênh (lần ${lanNay}/${TOI_DA_THU_KENH_LUOT} trong lượt quét): không gói nào mang chỉ số`);
    await nghi(tabId);
  } finally {
    kenhDangXep = false;
    nhaTab(ma);
    setTimeout(() => { kiemXongQuet().catch(() => {}); }, 5000);
  }
}

async function khamPha() {
  const ma = await xinTab('khám phá', 3);
  try {
    const tabId = await layTab();
    let ch = await st('kenh', '');
    if (!ch) {
      // Chưa biết mã kênh (máy mới, hoặc vừa xoá bộ nhớ): mở trang gốc để Studio tự chuyển hướng
      // sang /channel/<UC…>. Mã kênh trước đây CHỈ được nhặt từ href của các gói bắt được — nhưng
      // trang gốc gần như không gọi API nào, nên không có gói, nên không bao giờ có mã kênh, và
      // khamPha lặp lại mãi trang gốc: "trang chưa có dữ liệu → tải lại → chưa thấy video".
      // Đọc thẳng từ URL của tab sau khi chuyển hướng.
      log('chưa biết kênh — mở Studio để nhận diện');
      await moLink(tabId, 'https://studio.youtube.com/', null);
      for (let i = 0; i < 15 && !ch; i++) {
        try { ch = ((await chrome.tabs.get(tabId)).url.match(/\/channel\/(UC[\w-]+)/) || [])[1] || ''; } catch (e) {}
        if (!ch) await cho(1000);
      }
      if (ch) { await luu('kenh', ch); log(`kênh: ${ch}`); }
    }
    if (!ch) { await nghi(tabId); return; }
    log('tìm video từ trang Nội dung');
    await moLink(tabId, `https://studio.youtube.com/channel/${ch}/videos/upload`, null);
    await nghi(tabId);
  } finally { nhaTab(ma); }
}

// ═══ DANH SÁCH CHỤP BÙ CỦA TRẠM (12/10/2026) ═══
//
// Trạm nhìn thấy thứ tiện ích không thấy: bản chụp nào trên đĩa THẬT SỰ có số. `daChup` của tiện
// ích từng đánh dấu "xong" cho bản rỗng (lượt chồng), và mốc ấy không bao giờ được chụp lại — chỉ
// 17% bản chụp > 120h còn số. Đầu mỗi lượt quét, tiện ích hỏi trạm video nào thiếu số mới (quá
// ~20 giờ không có bản hợp lệ, tuổi ≤ 31 ngày) và chụp bù đúng những video ấy — nên mốc 72h,
// 96h, 7 ngày, 14 ngày… có thật cho mọi video. Trạm cũ không có cửa này → danh sách rỗng.
async function chupBuTuTram() {
  // Đang hỏi trạm cũng là "còn việc" — `kiemXongQuet` không được báo xong khi danh sách chưa về.
  soViecCho++;
  try {
    const host = await st('host', '');
    const kenh = (await st('ma_kenh', '')) || (await st('kenh', ''));
    if (!host || !kenh) return 0;
    // Chưa biết video nào (vừa nâng cấp/xoá bộ nhớ, khám phá chưa xong) → hỏi lại nhịp sau.
    if (!Object.keys(await st('videos', {})).length) return -1;
    let ds = [];
    try {
      const r = await fetchCoHan(`${host}/chup-bu?kenh=${encodeURIComponent(kenh)}`, {}, 60000);
      if (r.ok) ds = ((await r.json()) || {}).video || [];
    } catch (e) { log(`chụp bù: không hỏi được trạm (${e.message})`); return 0; }
    const videos = await st('videos', {});
    const ids = ds.map((x) => String((x && x.video_id) || '')).filter((id) => videos[id]);
    if (!ids.length) return 0;
    log(`trạm xin chụp bù ${ids.length} video thiếu số mới: ${ids.slice(0, 8).join(' ')}${ids.length > 8 ? ' …' : ''}`);
    for (const id of ids) chupVideo(id, null, { ep: true, bu: true }).catch((e) => log(`chụp bù ${id}: ${e}`));
    return ids.length;
  } finally { soViecCho--; }
}

// ---------------------------------------------------------------- lịch
let lanKhamPha = 0;
async function quetNgayHet(ids) {
  // Chu dong muon chup lai -> cho EP, ke ca moc da co (nut "Chup ngay
  // tat ca" cua popup, va lenh tu tram).
  if (!Object.keys(await st('videos', {})).length) await khamPha();
  const videos = await st('videos', {});
  // Nhãn, chụp nhẹ/đầy: `chupVideo` tự tính theo TUỔI THẬT lúc tới lượt (12/10/2026).
  for (const id of (ids && ids.length ? ids : Object.keys(videos))) {
    await chupVideo(id, null, { ep: true, tay: true });
  }
}

async function hoiLenh() {
  // Chu du an 02/09: "tao da ra lenh thi no cu lam chu" - lenh tay tren
  // tool phai EP chup lai tat ca. Tram giu lenh (mot lan lay la het),
  // tien ich hoi moi phut; luot theo lich khong qua duong nay nen luat
  // chong chup trung moc van giu nguyen.
  const host = await st('host', '');
  const kenh = (await st('ma_kenh', '')) || (await st('kenh', ''));
  if (!host || !kenh) return;
  let lenh = null;
  try {
    const r = await fetchCoHan(host + '/lenh-tien-ich?kenh=' + encodeURIComponent(kenh), {}, 20000);
    if (r.ok) lenh = await r.json();
  } catch (e) { return; }
  // Trạm kèm `ngay_bat_dau` của kênh vào MỌI câu trả lời (không phải lệnh một-lần-là-hết), nên
  // đổi ô "Ngày bắt đầu làm nội dung" trên tool là mắt cào biết trong một phút. Rỗng/thiếu thì
  // không đụng tới mốc đang giữ: trạm bản cũ chưa biết khoá này không được xoá mốc của tiện ích.
  if (lenh && lenh.ngay_bat_dau) {
    const moi = String(lenh.ngay_bat_dau).slice(0, 10);
    if (moi !== (await st('ngay_bat_dau', ''))) {
      await luu('ngay_bat_dau', moi);
      log(`ngày kênh bắt đầu làm nội dung: ${moi} — video đăng trước ngày này không chụp nữa`);
      await datLich();
    }
  }
  // 01/10/2026 — ngôn ngữ của kênh (kenh.yaml `ngon_ngu`): `loi-thoai.js` chọn đúng track phụ đề
  // theo nó (trước đây cứng 'ja'). Thiếu (trạm cũ) thì giữ giá trị đang có.
  if (lenh && lenh.ngon_ngu) {
    const nn = String(lenh.ngon_ngu).slice(0, 12);
    if (nn !== (await st('lt_ngon_ngu', ''))) await luu('lt_ngon_ngu', nn);
  }
  if (lenh && lenh.chup === 'het') {
    log('tram ra lenh: CHUP LAI TAT CA (lenh tay tu tool)');
    chupKenh({ tay: true }).catch(() => {});     // xếp hàng ưu tiên trước các video
    await quetNgayHet();
  }
}

async function datLich() {
  const videos = await st('videos', {});
  // Ngoài cửa sổ QUÉT NGÀY: vẫn đặt báo thức cho mốc TƯƠNG LAI, nhưng không khám phá, không
  // đặt báo thức "nổ ngay" cho mốc đã qua — các mốc ấy được đặt lại lúc Chrome mở để quét.
  const duocQuet = await choPhepQuet();
  if (!Object.keys(videos).length) {
    if (!duocQuet) { baoChan('khám phá video'); return; }
    if (Date.now() - lanKhamPha > 60000) {
      lanKhamPha = Date.now();
      await khamPha();
      if (Object.keys(await st('videos', {})).length) return datLich();
      log('chưa thấy video — kiểm tra đã đăng nhập Studio đúng kênh chưa');
    }
    return;
  }
  const daChup = await st('daChup', {});
  const co = new Set((await chrome.alarms.getAll()).map(a => a.name));
  const moc = await mocMs();
  const luot = await soLuot();
  let n = 0;
  let nBu = 0;
  let boQua = 0;
  for (const [id, v] of Object.entries(videos)) {
    // Video đời trước của kênh: không đặt lịch nào. Chặn ở `chupVideo` là đủ ĐÚNG, nhưng nếu chỉ
    // chặn ở đó thì Chrome vẫn nuôi 13 báo thức mỗi video cũ, và mỗi cái nổ ra một dòng nhật ký
    // "bỏ …" — nhật ký 200 dòng của tiện ích bị đẩy sạch, không còn thấy lượt chụp thật.
    if (ngoaiPhamVi(v, moc)) {
      boQua++;
      await chrome.alarms.clear(`ngay|${id}`);
      await chrome.alarms.clear(`bu|${id}`);
      for (const h of MOC) await chrome.alarms.clear(`snap|${id}|${h}`);
      continue;
    }
    const tuoi = (Date.now() - v.ngay_dang_ms) / 36e5;
    let thieuMocDaQua = false;
    for (const h of MOC) {
      if (tuoi > 24 * 35) break;
      const ten = `snap|${id}|${h}`;
      if (co.has(ten) || (daChup[id] || []).includes(`${h}h`)) continue;
      const khi = v.ngay_dang_ms + h * 36e5;
      if (khi > Date.now()) {
        await chrome.alarms.create(ten, { when: khi }); co.add(ten); n++;
      } else {
        thieuMocDaQua = true;
        // ═══ TỰ VÁ MỐC ĐÃ QUA MÀ CHƯA CÓ BÁO THỨC (29/09/2026) ═══
        //
        // Bản cũ CHỈ đặt báo thức khi `khi` còn ở tương lai — mốc nào đã qua lúc hàm này
        // chạy mà chưa từng đặt báo thức (`co` rỗng) thì bị BỎ VĨNH VIỄN, không bao giờ
        // xét lại. `datLich()` chạy lại mỗi lần service worker nạp (`onInstalled`/
        // `onStartup`/nạp module — xem cuối tệp), và đăng ký DevTools của agent KHÔNG BỀN
        // (`tests/test_nap_extension_devtools.py`: "mở lại là mất" — Chrome trước đây cấp
        // MỘT ID MỚI mỗi lần `Extensions.loadUnpacked`, xoá sạch `chrome.alarms` VÀ
        // `chrome.storage.local` của lượt trước). Ghim `key` trong manifest.json (29/09) làm
        // id ổn định qua các lần nạp, nhưng phòng khi alarm vẫn rơi vì lý do khác (Chrome bị
        // giết cứng giữa lượt, máy ảo khởi động lại…) — đặt báo thức nổ GẦN NHƯ NGAY thay vì
        // im lặng bỏ qua. Cùng hướng "thà chụp thừa còn hơn mất hẳn một mốc" mà nhánh "trễ"
        // của `onAlarm` bên dưới đã chọn cho báo thức fire muộn; đây là ca báo thức CHƯA TỪNG
        // tồn tại. `chupVideo`/`daChup` vẫn chặn chụp trùng nếu mốc này lỡ đã có số liệu.
        // 30/09/2026: CHỈ trong cửa sổ QUÉT NGÀY (xem `choPhepQuet`) — ngoài đó để dành.
        //
        // 12/10/2026: KHÔNG còn một báo thức cho MỖI mốc đã qua (13 cái/video, cùng nổ một
        // giây — gốc của bão chụp chồng). Mốc đã qua chỉ được GHI NHẬN ở đây; dưới vòng này đặt
        // đúng MỘT báo thức bù `bu|<id>` cho cả video: một bản chụp ở tuổi thật là số mới nhất
        // cho mọi mốc đã qua (`chupVideo` gộp chúng khi có số).
      }
    }
    const chuaTungCo = !(daChup[id] || []).length && tuoi <= 24 * 35;
    if (duocQuet && (thieuMocDaQua || chuaTungCo) && !co.has(`bu|${id}`) && !co.has(`ngay|${id}`)
        && !dangXepVideo.has(id) && !luot.ok[id] && (luot.thu[id] || 0) < TOI_DA_LUOT_THU_VIDEO) {
      await chrome.alarms.create(`bu|${id}`, { when: Date.now() + 2000 + 1000 * (nBu++) });
      co.add(`bu|${id}`); n++;
    }
  }
  if (!co.has('kham-pha')) await chrome.alarms.create('kham-pha', { periodInMinutes: 720 });
  if (!co.has('tu-kiem')) await chrome.alarms.create('tu-kiem', { periodInMinutes: 30 });
  // 02/09: chụp KÊNH mỗi ngày, không phải mỗi tuần — đọc kênh để quyết định
  // content là việc hằng ngày; 7 ngày/lần thì thư mục kenh/ trống trong khi
  // từng video đầy số. Xoá lịch tuần đời cũ còn nằm trong Chrome.
  if (!co.has('hoi-lenh')) await chrome.alarms.create('hoi-lenh', { periodInMinutes: 1 });
  if (co.has('kenh')) await chrome.alarms.clear('kenh');
  // VPS mở từng kênh đúng một phiên/ngày. Chụp số TOÀN KÊNH trước các lượt
  // video để bảng YPP luôn về đủ trong cửa 8 phút, rồi để agent đóng Chrome.
  // Lịch 360 phút đời cũ khiến Chrome tự cào bốn lần/ngày nếu bị giữ mở và
  // mâu thuẫn với hàng đợi tiết kiệm tài nguyên, nên thay hẳn bằng 1.440 phút.
  // 12/10/2026: chưa có số kênh hôm nay thì đặt lại (mỗi phút một lần là cùng) — trừ khi đang xếp
  // hàng chụp kênh, hoặc đã thử đủ `TOI_DA_THU_KENH_LUOT` lần trong lượt quét này.
  const homNayKenh = stamp().slice(0, 8);
  const baoKenh = await chrome.alarms.get('kenh-ngay');
  const chuaChupKenhHomNay = (await st('kenh_ngay_cuoi', '')) !== homNayKenh;
  const conLuotKenh = (await lanThuKenh()) < TOI_DA_THU_KENH_LUOT;
  if (duocQuet && !kenhDangXep
      && ((chuaChupKenhHomNay && conLuotKenh) || !baoKenh || baoKenh.periodInMinutes !== 1440)) {
    await chrome.alarms.clear('kenh-ngay');
    await chrome.alarms.create('kenh-ngay', { when: Date.now() + 1000, periodInMinutes: 1440 });
  }
  if (n) log(`đặt thêm ${n} lịch`);
  if (boQua) log(`bỏ ${boQua} video đăng trước ngày kênh bắt đầu làm nội dung`);
}

// ═══ BÁO THỨC MỐC NỔ TRỄ → LƯU THEO TUỔI THẬT, KHÔNG THEO NHÃN DỰ ĐỊNH ═══
//
// VPS giờ chỉ mở trình duyệt của MỘT kênh MỘT LẦN/NGÀY (phiên ngắn trước giờ đăng của kênh
// đó, xem `vm/KE-HOACH.md`). Báo thức mốc (`snap|id|h`, đặt trong `datLich()`) đặt cho đúng
// giờ `ngay_dang_ms + h*giờ`, nhưng Chrome không mở nên nó nằm chờ QUÁ HẠN — rồi cả chùm báo
// thức quá hạn (6h, 13h, 18h, 24h, 30h, 36h…) nổ gần như cùng lúc ngay khi Chrome mở lên.
// Báo thức tên "13h" khi đó chụp đúng lúc video đã 23 giờ tuổi, nhưng nếu vẫn lưu vào thư
// mục `13h/` thì đó là NHÃN DỰ ĐỊNH của báo thức, không phải tuổi thật của dữ liệu bên trong
// — `core/cong_thuc_v7.py` phía công cụ (mã `video_cua_kenh`/`da_co_video_thang`) từng tin
// thẳng nhãn này và chấm nhầm.
//
// Chọn LƯU THEO TUỔI THẬT thay vì BỎ QUA bản chụp trễ: bỏ qua là vứt một lượt vừa tốn ~1
// phút tải trang thật (đúng thứ mục "chỉ đánh dấu đã chụp khi thật sự có chỉ số" ở
// `chupVideo` đang tránh — thà chụp lại thừa còn hơn mất hẳn một mốc). Tool phía công cụ
// (`core/chi_so_ytb/gom.py: tuoi_that_gio`) đã tự tính lại tuổi thật từ `captured_at` trong
// mọi trường hợp, nên phần này không phải lưới an toàn DUY NHẤT — nhưng nhãn đúng ngay từ
// đầu giúp người đọc tay (`bang-tom-tat.csv`, `DOC-O-DAY.txt`) không bị nhãn sai đánh lừa,
// và không phải chờ bộ chấm suy ngược hộ.
//
// Ngưỡng "trễ": báo thức nhanh nhất trong MOC cách nhau 5–7 giờ, nên trễ quá 3 giờ đã đủ để
// phân biệt "đúng hẹn, lệch chút vì Studio trả chậm/`moLink` chờ tới 45 giây" khỏi "kẹt cả
// phiên, đợi hôm sau Chrome mới mở lại".
chrome.alarms.onAlarm.addListener(async (a) => {
  const [k, id, h] = a.name.split('|');
  // Cổng quét (xem `choPhepQuet`): báo thức nổ lúc Chrome đang mở cho việc ĐĂNG/BÌNH LUẬN thì
  // bỏ qua — báo thức một lần bị tiêu, nhưng `datLich()` đặt lại mọi mốc đã qua còn thiếu ngay
  // khi Chrome mở cho QUÉT NGÀY, nên không mất mốc nào.
  if (k !== 'tu-kiem' && !(await choPhepQuet())) { baoChan(`báo thức ${k}`); return; }
  if (k === 'snap') {
    // Tuổi THẬT lúc chụp: `chupVideo` đặt nhãn theo tuổi thật lúc tới lượt (12/10/2026: luôn
    // luôn, không chỉ khi lệch quá 3 giờ — báo thức xếp hàng sau vài video là đã lệch), ghi mốc
    // dự định `h` vào `_thong-tin.json`, và gộp mọi mốc đã qua vào đúng một bản chụp có số.
    await chupVideo(id, `${h}h`);
  }
  else if (k === 'ngay' || k === 'bu') {
    // `bu|<id>`: MỘT báo thức bù cho mọi mốc đã qua còn thiếu của video (xem `datLich`).
    // `ngay|<id>`: báo thức "video chưa từng có số liệu" của bản cũ — xử lý y như bù.
    await chupVideo(id, null);
  } else if (k === 'kham-pha') await khamPha();
  else if (k === 'kenh' || k === 'kenh-ngay') await chupKenh();
  else if (k === 'hoi-lenh') { moiTab(); await batDauQuetNeuCan(); await hoiLenh(); await kiemXongQuet(); }
  else if (k === 'tu-kiem') { moiTab(); await datLich(); }
});

// ═══ ĐẦU / CUỐI MỘT LƯỢT QUÉT NGÀY (30/09/2026) ═══
//
// Đầu lượt (mã lượt mới trong `che-do.json`): KHÁM PHÁ trước — Chrome giờ chỉ mở để quét mỗi
// ngày một lần, video đăng từ hôm qua chỉ được biết qua trang Nội dung (không còn gói "tình cờ"
// từ tab của máy đăng) — rồi đặt lịch: mốc đã qua nổ ngay, chụp kênh chạy trước.
async function batDauQuetNeuCan() {
  const c = await docCheDo();
  if (!c || c.che_do !== 'phien' || !(Date.now() < Number(c.quet_den || 0))) return false;
  const ma = String(c.ma || '');
  if (ma && (await st('quet_ma_bat_dau', '')) !== ma) {
    await luu('quet_ma_bat_dau', ma);
    await luu('quet_bat_dau_luc', Date.now());
    daBaoChan = false;
    log(`QUÉT NGÀY bắt đầu (lượt ${ma})`);
    try { lanKhamPha = Date.now(); await khamPha(); } catch (e) {}
    // 12/10/2026: số TOÀN KÊNH xếp hàng NGAY, trước mọi video (xem `chupKenh`).
    chupKenh().catch((e) => log(`chụp kênh: ${e}`));
  }
  await datLich();
  // Danh sách chụp bù của trạm — sau `datLich` để báo thức mốc của lượt này đã có chỗ đứng; trùng
  // video thì `chupVideo` tự bỏ (đang xếp hàng / đã có số trong lượt). Hỏi MỘT lần mỗi lượt mỗi
  // đời service worker: worker bị Chrome cho ngủ giữa lượt thì hàng đợi trong RAM mất — hỏi lại,
  // trạm chỉ trả những video còn thiếu.
  if (ma && daHoiBuLuot !== ma) {
    daHoiBuLuot = ma;
    if ((await chupBuTuTram().catch(() => 0)) < 0) daHoiBuLuot = '';
  }
  return true;
}
let daHoiBuLuot = '';

// Cuối lượt: không còn việc nào đang chạy hay sắp nổ (≤ 60 giây), đã chụp kênh hôm nay → báo
// agent (đổi TAB LÀM VIỆC sang `nghi.html?quet_xong=<mã>` — agent đọc danh sách tab ở cổng
// DevTools của kênh, không phụ thuộc trạm; kèm POST /quet-xong cho trạm như cũ). Mỗi mã lượt
// báo đúng một lần.
async function kiemXongQuet() {
  const c = await docCheDo();
  if (!c || c.che_do !== 'phien' || !(Date.now() < Number(c.quet_den || 0))) return false;
  const ma = String(c.ma || '');
  if (!ma || (await st('quet_ma_xong', '')) === ma) return false;
  if ((await st('quet_ma_bat_dau', '')) !== ma) return false;
  if (Date.now() - Number(await st('quet_bat_dau_luc', 0)) < 60000) return false;
  if (tabBan() || ltDoi) return false;
  // Chưa có số toàn kênh hôm nay thì chưa xong — trừ khi đã thử đủ lần trong lượt này (khi ấy báo
  // xong để agent đi tiếp; phía tool `_du_lieu_kenh_da_ve_hom_nay` thấy thiếu `kenh-<ngày>` → lượt
  // quét sau trong ngày thử lại, và người gác báo "số liệu kênh cũ").
  const homNay = stamp().slice(0, 8);
  if ((await st('kenh', '')) && (await st('kenh_ngay_cuoi', '')) !== homNay
      && (await lanThuKenh()) < TOI_DA_THU_KENH_LUOT) return false;
  const sap = (await chrome.alarms.getAll()).filter((x) =>
    (/^(snap|ngay|bu)\|/.test(x.name) || x.name === 'kenh-ngay') && (x.scheduledTime || 0) <= Date.now() + 60000);
  if (sap.length) return false;
  await luu('quet_ma_xong', ma);
  log(`QUÉT NGÀY xong (lượt ${ma}) — báo agent`);
  try {
    const tabId = await layTab();
    await chrome.tabs.update(tabId, { url: TRANG_NGHI + '?quet_xong=' + encodeURIComponent(ma), active: false });
  } catch (e) {}
  const host = await st('host', '');
  const kenh = (await st('ma_kenh', '')) || (await st('kenh', ''));
  if (host && kenh) {
    try {
      await fetchCoHan(host + '/quet-xong', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kenh }) }, 20000);
    } catch (e) {}
  }
  return true;
}

// Địa chỉ trạm nhận lấy từ `cau-hinh.json` đi kèm thư mục tiện ích.
//
// ═══ VÌ SAO PHẢI GHI VÀO TỆP, KHÔNG CHỈ VÀO Ô NHẬP ═══
//
// Gỡ tiện ích rồi cài lại — việc phải làm mỗi lần cập nhật bản chưa đóng gói — thì Chrome
// **xoá sạch `chrome.storage.local`**, kéo theo địa chỉ trạm nhận. Mà khi địa chỉ trống,
// tiện ích không báo lỗi: nó lặng lẽ quay về ghi vào thư mục Tải xuống của chính máy ảo.
// Nhìn từ ngoài thì mọi thứ vẫn chạy, chỉ là không gói nào về tới nơi cần.
//
// Đã mất một lượt chụp vì đúng chuyện này, 31/08/2026.
//
// Tệp cấu hình nằm trong thư mục tiện ích nên nó sống sót qua mọi lần cài lại. Công cụ ghi
// sẵn địa chỉ máy của bạn vào đó lúc bấm "Lưu tiện ích ra máy".
//
// CHỈ điền khi ô đang trống — người dùng tự sửa địa chỉ thì lần cài sau không bị ghi đè.
// ---------------------------------------------------------------- kho lời thoại
//
// ═══ HÀNG ĐỢI LỜI THOẠI — AI GIỮ, VÌ SAO Ở ĐÂY ═══
//
// `loi-thoai.js` sống trong TRANG, nên nó chết mỗi lần sang video kế. Hàng đợi phải nằm ở
// service worker này: nó là thứ duy nhất sống qua các lần điều hướng của tab.
//
// Đường đi một phiên (xem `vm/agent.lay_loi_thoai` và `Tram.can_lay_loi_thoai`):
//   1. agent hỏi trạm `GET /loi-thoai/can-lay?kenh=…&k=8`, mở tab video ĐẦU kèm dấu
//      `shopapi_lt=1`;
//   2. `loi-thoai.js` hút bảng phụ đề rồi báo về đây;
//   3. đây POST `/loi-thoai` (chữ, hoặc cờ `khong_co`), rồi tự hỏi trạm danh sách và ĐIỀU
//      HƯỚNG chính tab ấy sang video kế sau 4–8 giây NGẪU NHIÊN;
//   4. hết danh sách (hay quá trần) thì đưa tab về trang nghỉ và xoá hàng đợi.
//
// Nhịp ngẫu nhiên và trần 8 video là luật sắt: đây là trình duyệt ĐANG ĐĂNG NHẬP tài khoản
// kênh — thứ duy nhất trong cả dây chuyền còn vào được YouTube từ địa chỉ mạng này. Cào dồn
// là cách nhanh nhất để mất luôn nó, và mất nó là mất cả Studio lẫn đăng lẫn bình luận.
const LT_TOI_DA = 8;             // trần video mỗi phiên — khớp `Tram.K_CAN_LAY`
const LT_NGHI_MIN_MS = 4000;     // chờ ít nhất 4 giây giữa hai video
const LT_NGHI_MAX_MS = 8000;     // … và nhiều nhất 8 giây
// Trần cả lượt, KHỚP ĐÚNG khoảng agent còn chờ (`LT_TOI_DA` × `CHO_MOI_VIDEO_LOI_THOAI_GIAY`
// = 8 × 12 giây). Đây không phải một con số cho đẹp: hết khoảng ấy agent đi tiếp sang bước
// ĐĂNG, và bước đăng lái trình duyệt bằng PyAutoGUI (bấm chuột trên màn hình thật). Nếu hàng
// đợi này còn sống và còn `chrome.tabs.update` sang video kế thì nó ĐỔI TRANG dưới tay người
// đang bấm — đúng kiểu hỏng khó tìm nhất. Thà bỏ dở vài video còn hơn giẫm vào lượt đăng;
// phần chưa hút thì phiên mai lấy tiếp (trạm vẫn xếp chúng đầu bảng).
const LT_HAN_PHIEN_MS = LT_TOI_DA * 25 * 1000;   // 22/09: 12→25s, hút thật mỗi video ~20s
let ltDoi = null;                // {daLam:Set, dem:{co,khong_co,loi}, batDau}

// ═══ AI LÀ "TAB LỜI THOẠI" — SỰ THẬT PHẢI NẰM Ở ĐÂY, KHÔNG NẰM TRONG URL ═══
//
// Đo thật 22/09/2026 (phiên TL1-T7, 09:52–10:03): kết quả "0 lấy được · 0 không có · 8 chưa
// về", và LevelDB của tiện ích không có một dòng log nào chứa "lời thoại". Tệp phiên
// Chromium `Session_13434519629720236` giải thích vì sao: nó chứa CẢ HAI địa chỉ cho cùng
// một video — `…watch?v=vidGiaee003&shopapi_lt=1` VÀ `…watch?v=vidGiaee003`. Tab mở đúng
// địa chỉ kèm dấu, rồi YouTube tự `replaceState` gỡ dấu đi. `loi-thoai.js` chạy ở
// `document_idle`, tới lúc ấy dấu đã mất, và nó `return` trong im lặng.
//
// Đường mở tab của agent KHÔNG sai (launcher thứ hai chỉ chuyển địa chỉ cho instance đang
// chạy — đúng thiết kế). Sai là chỗ ta CẤT sự thật: một tham số URL là thứ YouTube được
// phép viết lại, nên nó không bao giờ nên là nguồn duy nhất.
//
// `chrome.tabs.onUpdated` nhận `changeInfo.url` với địa chỉ **gốc**, trước lượt chuẩn hoá —
// nên đây là nguồn chính. Không thêm quyền nào: `tabs` đã có trong manifest.
// Đăng ký ở TẦNG NGOÀI CÙNG (không trong hàm) là bắt buộc với service worker MV3: chỉ
// listener tầng ngoài mới ĐÁNH THỨC worker đang ngủ khi sự kiện tới.
//
// Ghi thêm xuống `chrome.storage.local`: `ltTabId` trong RAM chết theo mỗi lần worker ngủ,
// mà lượt hút kéo dài cả phút. Đọc lại từ đĩa là lớp vá cho đúng cái chết ấy.
let ltTabId = null;

const ltDatTab = async (tabId) => {
  ltTabId = tabId;
  try { await luu('lt_tab', tabId); } catch (e) {}
};

const ltLaTabLt = async (tabId) => {
  if (tabId == null) return false;
  if (ltTabId === tabId) return true;
  // Worker vừa tỉnh lại sau một giấc ngủ: RAM trắng, hỏi đĩa.
  const cat = await st('lt_tab', null);
  if (cat === tabId) { ltTabId = tabId; return true; }
  return false;
};

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo && typeof changeInfo.url === 'string'
      && changeInfo.url.includes('shopapi_lt=1')) {
    ltDatTab(tabId).then(() => log(`lời thoại: nhận tab #${tabId} (dấu shopapi_lt trong địa chỉ gốc)`));
  }
});

const ltNghiMs = () => LT_NGHI_MIN_MS + Math.floor(Math.random() * (LT_NGHI_MAX_MS - LT_NGHI_MIN_MS + 1));
const ltUrl = (ma) => `https://www.youtube.com/watch?v=${ma}&shopapi_lt=1`;

async function ltDanhSach(host, kenh) {
  try {
    const r = await fetch(`${host}/loi-thoai/can-lay?kenh=${encodeURIComponent(kenh)}&k=${LT_TOI_DA}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    if (j && j.loi) log(`lời thoại: trạm nói ${j.loi}`);
    if (j && j.ngon_ngu) { try { await luu('lt_ngon_ngu', String(j.ngon_ngu).slice(0, 12)); } catch (e) {} }
    return (j && j.video) || [];
  } catch (e) { log(`lời thoại: không hỏi được danh sách (${e.message})`); return []; }
}

// Gửi MỘT bản ghi về trạm. `khong_co` là một câu trả lời THẬT ("video này không có bảng phụ
// đề"), không phải một lượt hỏng — trạm cất nó lại để phiên sau thôi hỏi lại video ấy.
async function ltGui(host, kenh, m) {
  try {
    const r = await fetch(host + '/loi-thoai', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kenh, video_id: m.video_id, tieu_de: m.tieu_de || '',
        ngon_ngu: '', dai_giay: m.dai_giay || 0, text: m.text || '',
        khong_co: !!m.khong_co, nguon: 'trinh-duyet' }) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return true;
  } catch (e) { log(`lời thoại ${m.video_id}: không gửi được về trạm (${e.message})`); return false; }
}

async function ltNhanBaoCao(msg, tabId) {
  const host = await st('host', HOST_MAC_DINH);
  const kenh = (await st('ma_kenh', '')) || (await st('kenh', '')) || 'kenh';
  if (!host) { log('lời thoại: chưa có địa chỉ trạm — bỏ qua'); return; }
  // Service worker MV3 ngủ giữa chừng là mất hàng đợi (và mất luôn cái `await cho(4–8s)`
  // ngay dưới). Giữ thức như mọi lượt dài khác ở tệp này. KHÔNG gọi `tatGiuThuc()` khi
  // xong: nó dùng chung một đồng hồ với lượt chụp Studio, và tắt hộ người khác thì lượt
  // chụp đang chạy mất lưới giữ thức. Một `getPlatformInfo` mỗi 20 giây tới hết phiên là
  // giá rẻ hơn hẳn một hàng đợi bị bỏ dở.
  batGiuThuc();
  if (!ltDoi) ltDoi = { daLam: new Set(), dem: { co: 0, khong_co: 0, loi: 0 }, batDau: Date.now() };
  ltDoi.daLam.add(msg.video_id);

  if (msg.text) {
    ltDoi.dem.co += 1;
    log(`lời thoại ${msg.video_id}: ${msg.text.length} ký tự → trạm`);
  } else {
    ltDoi.dem.khong_co += 1;
    log(`lời thoại ${msg.video_id}: KHÔNG có bảng phụ đề (${msg.loi || 'không rõ'})`);
  }
  if (!(await ltGui(host, kenh, msg))) ltDoi.dem.loi += 1;

  // Hết trần video, hoặc hết trần thời gian → đóng lượt. Kiểm CẢ HAI: một video có bảng
  // phụ đề dài nạp lâu, tám cái như thế là vượt hẳn khoảng agent còn chờ.
  const quaHan = Date.now() - ltDoi.batDau > LT_HAN_PHIEN_MS;
  if (ltDoi.daLam.size >= LT_TOI_DA || quaHan) return ltKetThuc(tabId, quaHan ? 'quá hạn lượt' : 'đủ trần');

  const ds = await ltDanhSach(host, kenh);
  const tiep = (ds || []).find((v) => v && v.video_id && !ltDoi.daLam.has(v.video_id));
  if (!tiep) return ltKetThuc(tabId, 'hết danh sách');

  const nghi = ltNghiMs();
  // Kiểm hạn MỘT LẦN NỮA, có tính cả khoảng nghỉ sắp tới: sang video kế rồi mới phát hiện
  // quá hạn là đã điều hướng tab một lần quá muộn — đúng lần có thể rơi trúng lượt đăng.
  if (Date.now() + nghi > ltDoi.batDau + LT_HAN_PHIEN_MS) return ltKetThuc(tabId, 'quá hạn lượt');
  log(`lời thoại: nghỉ ${Math.round(nghi / 1000)}s rồi sang ${tiep.video_id}`);
  await cho(nghi);
  // Chính ta điều hướng thì ta BIẾT tab nào — đặt trước, không đợi `onUpdated` (sự kiện ấy
  // vẫn tới và đặt lại cùng giá trị, nhưng đặt sẵn thì không có khe hở nào ở giữa).
  await ltDatTab(tabId);
  try { await chrome.tabs.update(tabId, { url: ltUrl(tiep.video_id) }); }
  catch (e) { ltKetThuc(tabId, 'tab đã đóng'); }
}

async function ltKetThuc(tabId, vi_sao) {
  const d = (ltDoi && ltDoi.dem) || { co: 0, khong_co: 0, loi: 0 };
  log(`lời thoại: xong lượt (${vi_sao}) — ${d.co} lấy được · ${d.khong_co} không có · ${d.loi} lỗi gửi`);
  ltDoi = null;
  // Nhả tab: từ giờ nó là tab thường. Người ngồi xem tiếp trong đúng tab ấy không bị hút oan.
  ltTabId = null;
  try { await luu('lt_tab', null); } catch (e) {}
  // Đưa tab về trang nghỉ, KHÔNG đóng: đóng tab cuối cùng của cửa sổ là Chrome thoát, và
  // phiên còn cần trình duyệt sống cho bước đăng / trả lời bình luận sau đó.
  try { await chrome.tabs.update(tabId, { url: TRANG_NGHI }); } catch (e) {}
}

async function napCauHinh() {
  try {
    const r = await fetch(chrome.runtime.getURL('cau-hinh.json'));
    const c = await r.json();
    if (c && c.host && !(await st('host', ''))) {
      await luu('host', c.host); log(`địa chỉ trạm nhận từ cấu hình: ${c.host}`);
    }
    // Agent trên máy ảo điền sẵn mã kênh (02/09/2026) — người dùng khỏi gõ
    // popup. Chỉ điền khi ô đang trống, ai tự sửa thì không bị ghi đè.
    if (c && c.ma_kenh && !(await st('ma_kenh', ''))) {
      await luu('ma_kenh', c.ma_kenh); log(`mã kênh từ cấu hình: ${c.ma_kenh}`);
    }
    // Ngày kênh bắt đầu làm nội dung — đường DỰ PHÒNG (xem `mocMs()`). Tệp trong thư mục tiện
    // ích sống sót qua mọi lần cài lại, nên mốc còn nguyên cả khi Chrome xoá `storage.local` và
    // trạm chưa kịp trả lời. Đường chính là `/lenh-tien-ich`, nó ghi đè cái này.
    if (c && c.ngay_bat_dau && !(await st('ngay_bat_dau', ''))) {
      await luu('ngay_bat_dau', String(c.ngay_bat_dau).slice(0, 10));
      log(`ngày kênh bắt đầu (từ cấu hình): ${String(c.ngay_bat_dau).slice(0, 10)}`);
    }
  } catch (e) {}
}

chrome.runtime.onInstalled.addListener(async () => {
  await napCauHinh();
  const v = chrome.runtime.getManifest().version;
  const cu = await st('phien_ban', '');
  if (cu !== v) {
    await chrome.alarms.clearAll();
    await luu('videos', {});
    await luu('phien_ban', v);
    log(`nâng cấp ${cu || '—'} → ${v}`);
  }
  datLich();
});
chrome.runtime.onStartup.addListener(() => datLich());
// DevTools `Extensions.loadUnpacked` có thể nạp lại một extension đã tồn tại
// mà không phát `onInstalled`, còn `onStartup` đã trôi qua trước lúc agent
// nạp mắt cào. Khởi tạo ngay khi service worker sống; các alarm và dấu ngày
// đều idempotent nên gọi lại không sinh lượt quét thứ hai.
// 30/09/2026: nạp trong cửa sổ QUÉT NGÀY → mở đầu lượt quét (khám phá + đặt lịch); ngoài cửa
// sổ → chỉ đặt lịch mốc tương lai (xem `choPhepQuet`).
batDauQuetNeuCan().catch(() => false)
  .then((q) => { if (!q) return datLich().catch((e) => log(`khởi tạo lịch: ${e}`)); });

// ---------------------------------------------------------------- popup
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  (async () => {
    if (msg.type === 'capture') { await luuCapture(msg, sender); reply({ ok: true }); }
    else if (msg.type === 'trang_thai') {
      let hostOk = false;
      const host = await st('host', HOST_MAC_DINH);
      // Không có địa chỉ máy chủ là chuyện BÌNH THƯỜNG, không phải hỏng: dữ liệu ghi thẳng
      // vào thư mục Tải xuống. Trạng thái phải nói đúng thế, chứ hiện "✗ không tới được"
      // sẽ làm người dùng tưởng hỏng và đi sửa một thứ vốn không cần có.
      if (host) { try { hostOk = (await fetch(host + '/')).ok; } catch (e) {} }
      reply({ host, hostOk, luu_may: !host, thu_muc: await st('thu_muc', 'chi-so-youtube'),
        kenh: await st('kenh', ''), ma_kenh: await st('ma_kenh', ''),
        videos: await st('videos', {}), daChup: await st('daChup', {}),
        lich: (await chrome.alarms.getAll()).map(a => ({ name: a.name, when: a.scheduledTime })),
        endpoints, logs: logs.slice(0, 30) });
    }
    else if (msg.type === 'cau_hinh') {
      await luu('host', msg.host || '');
      await luu('ma_kenh', msg.ma_kenh || '');
      if (msg.thu_muc !== undefined) await luu('thu_muc', msg.thu_muc || 'chi-so-youtube');
      reply({ ok: true });
    }
    else if (msg.type === 'quet_ngay') {
      await quetNgayHet(msg.ids);
      reply({ ok: true });
    }
    else if (msg.type === 'doi_thu') {
      // trang-chu.js gom kênh đứng sau video được đề xuất — chuyển về trạm để
      // nối vào sổ đối thủ của kênh (trạm tự khử trùng). Không có trạm thì
      // thôi: đây là dữ liệu phụ, không đáng ghi file lằng nhằng vào máy ảo.
      const host = await st('host', HOST_MAC_DINH);
      const kenh = (await st('ma_kenh', '')) || (await st('kenh', '')) || 'kenh';
      const ds = (msg.danh_sach || []).slice(0, 300);
      if (host && ds.length) {
        try {
          const r = await fetch(host + '/doi-thu', { method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kenh, danh_sach: ds }) });
          const j = await r.json().catch(() => ({}));
          log(`trang chủ: thấy ${ds.length} kênh, trạm nhận thêm ${j.them ?? '?'} đối thủ mới`);
        } catch (e) { log(`trang chủ: không gửi được về trạm (${e})`); }
      } else if (!host) { log('trang chủ: chưa có địa chỉ trạm — bỏ qua'); }
      reply({ ok: true });
    }
    else if (msg.type === 'zoom') {
      // trang-chu.js xin thu nhỏ trang chủ để mỗi lần nạp được nhiều thẻ hơn, rồi xin
      // trả về 100% khi xong. Chỉ đụng đúng tab đang gửi.
      try { if (sender.tab && sender.tab.id) await chrome.tabs.setZoom(sender.tab.id, Number(msg.muc) || 1); } catch (e) {}
      reply({ ok: true });
    }
    else if (msg.type === 'trang_chu') {
      // ═══ TRANG CHỦ v2 (05/09/2026): gửi TỪNG VIDEO, không chỉ link kênh ═══
      // Chủ dự án: "mở trang chủ, thu nhỏ, lấy hết link về, chuyển cho tool — tool làm
      // việc phía sau". Trình duyệt không lọc gì; trạm ghi `trang-chu.csv`, tra kênh
      // bằng yt-dlp, lọc 雑学/loại trừ rồi mới nối vào hộp thư. Trạm CŨ chưa có cửa
      // /trang-chu thì rớt về /doi-thu như bản 2.4 — không mất lượt quét.
      const host = await st('host', HOST_MAC_DINH);
      const kenh = (await st('ma_kenh', '')) || (await st('kenh', '')) || 'kenh';
      const video = (msg.video || []).slice(0, 2000);
      const ds = (msg.danh_sach || []).slice(0, 600);
      if (!host) { log('trang chủ: chưa có địa chỉ trạm — bỏ qua'); reply({ ok: false }); return; }
      let xong = false;
      try {
        const r = await fetch(host + '/trang-chu', { method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kenh, video, danh_sach: ds, href: msg.href, so_lan_cuon: msg.so_lan_cuon }) });
        if (r.ok) {
          const j = await r.json().catch(() => ({}));
          log(`trang chủ: ${video.length} video sau ${msg.so_lan_cuon || '?'} lần cuộn → trạm nhận, +${j.kenh_moi ?? '?'} đối thủ mới, loại ${j.bi_loai ?? '?'} kênh`);
          xong = true;
        }
      } catch (e) { log(`trang chủ: /trang-chu lỗi (${e}) — thử đường cũ`); }
      if (!xong && ds.length) {
        try {
          const r = await fetch(host + '/doi-thu', { method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kenh, danh_sach: ds }) });
          const j = await r.json().catch(() => ({}));
          log(`trang chủ (đường cũ): ${ds.length} kênh, trạm nhận thêm ${j.them ?? '?'}`);
        } catch (e) { log(`trang chủ: không gửi được về trạm (${e})`); }
      }
      reply({ ok: true });
    }
    else if (msg.type === 'lt_hoi') {
      // `loi-thoai.js` hỏi: "tôi có phải tab lời thoại không?". Nó KHÔNG tự trả lời được
      // bằng địa chỉ của chính mình nữa — YouTube gỡ dấu `shopapi_lt` trước khi nó chạy
      // (đo thật 22/09/2026, xem khối `ltTabId` ở trên).
      // Cổng quét: lời thoại chỉ hút trong cửa sổ QUÉT NGÀY (agent mở trang xem kèm dấu ở đó).
      // 01/10/2026: kèm ngôn ngữ kênh để trang chọn đúng track phụ đề (rỗng → trang tự lùi 'ja').
      reply({ la_tab_lt: (await choPhepQuet()) && await ltLaTabLt(sender.tab && sender.tab.id),
              ngon_ngu: await st('lt_ngon_ngu', '') });
    }
    else if (msg.type === 'tim_kiem_hoi') {
      // 01/10/2026 — `trang-chu.js` xong lượt trang chủ, hỏi có cụm TÌM KIẾM nào cho kênh không
      // (`tu_khoa_tim` của ngach.yaml, trạm xoay 3 cụm/ngày). Chỉ trong cửa sổ QUÉT NGÀY; trạm cũ /
      // nhóm không khai → danh sách rỗng, trang không làm gì thêm.
      let tu = [];
      try {
        const host = await st('host', HOST_MAC_DINH);
        const kenh = (await st('ma_kenh', '')) || (await st('kenh', ''));
        if (host && kenh && (await choPhepQuet())) {
          const r = await fetch(`${host}/tim-kiem/can-tim?kenh=${encodeURIComponent(kenh)}`);
          if (r.ok) {
            const j = await r.json().catch(() => ({}));
            tu = ((j && j.tu_khoa) || []).map((x) => String(x || '')).filter(Boolean).slice(0, 3);
            if (tu.length) log(`tìm kiếm theo chủ đề: ${tu.length} cụm (${tu.join(' · ').slice(0, 120)})`);
          }
        }
      } catch (e) { tu = []; }
      reply({ tu_khoa: tu });
    }
    else if (msg.type === 'cho_phep_quet') {
      // `trang-chu.js` hỏi trước khi cuộn/gom trang chủ (cổng quét, 30/09/2026).
      const ok = await choPhepQuet();
      if (!ok) baoChan('trang chủ');
      reply({ ok });
    }
    else if (msg.type === 'lt_log') {
      // Một dòng log từ trong TRANG. Hôm 22/09 ta mù hoàn toàn vì content script thoát
      // lặng lẽ: không log, không gói, không gì. Nay nó nói ra cả khi nó QUYẾT ĐỊNH KHÔNG
      // CHẠY — đọc LevelDB (hay popup tiện ích) là thấy ngay nó có được kích hay không.
      log(`lời thoại[trang]: ${String(msg.chu || '').slice(0, 200)}`);
      reply({ ok: true });
    }
    else if (msg.type === 'loi_thoai') {
      // `loi-thoai.js` vừa hút xong (hay vừa thấy video không có bảng phụ đề) MỘT video.
      // Trả lời NGAY rồi mới làm việc dài: phần sau có `await cho(4–8 giây)` và
      // `chrome.tabs.update`, mà trang gửi tin sắp bị điều hướng đi — giữ nó ngồi chờ
      // một phản hồi không bao giờ tới là vô ích. Xem hàng đợi ở `ltNhanBaoCao`.
      reply({ ok: true });
      const tabId = sender.tab && sender.tab.id;
      if (tabId != null) ltNhanBaoCao(msg, tabId).catch((e) => log(`lời thoại: ${e}`));
    }
    else if (msg.type === 'kham_pha') { khamPha(); reply({ ok: true }); }
    else if (msg.type === 'chup_kenh') { chupKenh({ tay: true }); reply({ ok: true }); }
    else if (msg.type === 'xoa_lich') {
      await chrome.alarms.clearAll(); await luu('daChup', {});
      log('xoá lịch sử chụp, đặt lại lịch');
      if (!Object.keys(await st('videos', {})).length) { lanKhamPha = 0; await khamPha(); }
      await datLich(); reply({ ok: true });
    }
    else reply({});
  })();
  return true;
});
