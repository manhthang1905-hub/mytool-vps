// Trang XEM của YouTube: MỞ BẢNG PHỤ ĐỀ → GOM CHỮ → gửi về trạm.
//
// ═══ VÌ SAO CON MẮT NÀY PHẢI NẰM TRONG TRÌNH DUYỆT (22/09/2026) ═══
//
// Khâu đầu của sản xuất cần LỜI THOẠI video đối thủ. Tool ở nhà lấy nó bằng `yt-dlp` và
// `youtube-transcript-api` — và đêm 22/09/2026 cả hai chết cùng lúc trên VPS: YouTube chặn
// theo ĐỊA CHỈ MẠNG (`IpBlocked`, nguyên văn *"You are doing requests from an IP belonging
// to a cloud provider"*), và cái chặn nặng dần THEO SỐ LƯỢT HỎI. Cookie, đổi
// `player_client`, nâng yt-dlp, cắm proxy: không cứu được đường tải tiếng.
//
// Nhưng từ ĐÚNG địa chỉ ấy, trình duyệt của kênh (phiên Chromium chống vân tay mà
// `vm/agent.py` mở mỗi sáng) vào YouTube bình thường — đêm 21/09/2026 chạy trọn 4 phiên
// không lỗi. Nên chữ đi đường này: một tab thật, một người xem thật, một bảng phụ đề mà
// YouTube tự mở ra cho bất kỳ ai bấm vào.
//
// ═══ ĐI NHƯ NGƯỜI XEM, KHÔNG CÀO DỒN ═══
//
// Đây là trình duyệt ĐANG ĐĂNG NHẬP tài khoản kênh — thứ đắt nhất và không thay thế được
// trong cả dây chuyền. Mất nó là mất luôn Studio, mất đăng, mất trả lời bình luận. Nên:
// tối đa 8 video một phiên, mỗi video chờ 4–8 giây NGẪU NHIÊN (nhịp do `background.js`
// giữ), không mở song song, không lượt nào chạy khi phiên đã đóng tab.
//
// ═══ BÁM SELECTOR NÀO, VÀ VÌ SAO TIN NÓ ═══
//
// Giao diện YouTube của các kênh này là TIẾNG NHẬT (tài khoản Nhật) — nút không ghi
// "Show transcript" mà ghi "文字起こしを表示", và nó còn nằm sau nút "...もっと見る" dưới
// phần mô tả. Bám CHỮ TRÊN NÚT là hỏng ngay khi đổi ngôn ngữ giao diện, hoặc khi Google
// đổi cách dịch. Nên chỉ bám TÊN THẺ web-component của YouTube — chúng là tên nội bộ, một
// ngôn ngữ, không đổi theo tài khoản:
//
//   · `ytd-video-description-transcript-section-renderer` — cả khối "Bản chép lời" trong
//     phần mô tả; cái nút cần bấm là `button` duy nhất trong khối ấy.
//   · `#description-inline-expander` + `#expand` — chỗ giấu khối trên ("...more"). `#expand`
//     là id nội bộ của `ytd-text-inline-expander`, không phải nhãn chữ.
//   · `ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"]`
//     — bảng phụ đề khi đã mở. `target-id` là khoá nội bộ YouTube dùng để tự định tuyến
//     panel; nó có mặt kể cả lúc panel còn đang ẩn (nên phải kiểm CẢ `visibility`).
//   · `ytd-transcript-segment-renderer` — từng đoạn phụ đề; chữ ở `.segment-text`.
//   · `video` (thẻ HTML5 thuần) — `duration` để biết video dài bao nhiêu giây.
//
// Cái yếu nhất trong danh sách là `target-id`; nên khi không tìm ra panel theo `target-id`
// thì còn một đường lui: tìm thẳng `ytd-transcript-renderer` ở bất cứ đâu trong trang.
// Panel mở ra mà KHÔNG có đoạn nào (hoặc không mở được) thì báo về trạm là "khong-co" —
// một câu trả lời thật, để phiên sau thôi hỏi lại video ấy.
//
// Mọi thứ ở đây bọc trong try/catch và có TRẦN THỜI GIAN: script này chạy trong trình
// duyệt thật của kênh, nó không được phép treo một tab lại mãi.
(() => {
  'use strict';
  if (location.hostname !== 'www.youtube.com') return;
  if (location.pathname !== '/watch') return;

  // `v` KHÔNG bị YouTube gỡ (nó là thứ định danh trang), nên vẫn lấy mã từ địa chỉ.
  const MA = (new URLSearchParams(location.search).get('v') || '').slice(0, 11);
  if (!/^[\w-]{11}$/.test(MA)) return;

  // 12→30 và 12→20 (22/09/2026, 12:05): với 12s, 6/6 video một lượt trượt ở "không thấy khối"
  // — trong khi soi DOM bằng DevTools (trang đã dựng xong) thì khối có. Lúc hút, extension còn
  // đang cào Studio song song (log `→host … tab-overview 305 KB` xen giữa), máy 4 nhân nghẽn,
  // trang xem dựng chậm hơn 12s. Trần rộng hơn; agent chờ 25s/video nên vẫn khớp.
  const CHO_MO_TA_MS = 30000;      // trần chờ khối "Bản chép lời" hiện ra trong mô tả
  const CHO_PANEL_MS = 20000;      // trần chờ bảng phụ đề mở sau khi bấm
  const CHO_DOAN_MS = 15000;       // trần chờ các đoạn phụ đề nạp xong
  const NHIP_MS = 400;             // nhịp hỏi lại DOM

  const cho = (ms) => new Promise((r) => setTimeout(r, ms));
  const goi = (msg) => new Promise((r) => {
    try { chrome.runtime.sendMessage(msg, (tl) => r(tl || {})); } catch (e) { r({}); }
  });
  const noi = (chu) => goi({ type: 'lt_log', chu });

  // ═══ "TÔI CÓ PHẢI TAB LỜI THOẠI KHÔNG" — BA NGUỒN, KHÔNG CÒN DỰA VÀO URL ═══
  //
  // Bản trước hỏi đúng một chỗ: `location.search` có `shopapi_lt` không. Đo thật
  // 22/09/2026 (phiên TL1-T7): tab mở ĐÚNG `…&shopapi_lt=1` (tệp phiên Chromium
  // `Session_13434519629720236` còn giữ cả hai địa chỉ), nhưng YouTube `replaceState` gỡ
  // dấu TRƯỚC khi tệp này chạy (`document_idle`) — nên cửa đóng sập, 8/8 video "chưa về",
  // và không một dòng log nào để lần theo.
  //
  //   1. `background.js` — nó bắt `chrome.tabs.onUpdated`, nơi địa chỉ còn NGUYÊN dấu.
  //      Đây là nguồn chính, và nó không nằm trong tay YouTube.
  //   2. cờ `sessionStorage` do `lt-dau.js` cắm ở `document_start` (sớm hơn replaceState).
  //      Đường lui cho ca service worker đang ngủ lúc tab mở quá nhanh.
  //   3. địa chỉ còn dấu — nết cũ, giữ lại vì có trang YouTube không chuẩn hoá.
  //
  // Đọc cờ rồi XOÁ ngay: cờ có giá trị đúng một lần nạp trang. Lần nạp kế (background điều
  // hướng, địa chỉ lại kèm dấu) thì `lt-dau.js` cắm lại; còn người ngồi xem tiếp trong đúng
  // tab ấy sau khi lượt xong thì không bị hút oan.
  const coSession = () => {
    try {
      const co = sessionStorage.getItem('shopapi_lt') === '1';
      if (co) sessionStorage.removeItem('shopapi_lt');
      return co;
    } catch (e) { return false; }
  };

  const duocKich = async () => {
    const tuSession = coSession();
    const tuUrl = new URLSearchParams(location.search).has('shopapi_lt');
    const tuBg = !!(await goi({ type: 'lt_hoi' })).la_tab_lt;
    if (tuBg || tuSession || tuUrl) {
      await noi(`${MA}: chạy (background=${tuBg} · session=${tuSession} · url=${tuUrl})`);
      return true;
    }
    // KHÔNG im lặng. Hôm 22/09 chính sự im lặng ở đây làm mất cả buổi đi tìm.
    await noi(`${MA}: BỎ QUA — không phải tab lời thoại (background=0 · session=0 · url=0)`);
    return false;
  };

  // Chờ tới khi `lay()` trả về thứ khác rỗng, hoặc hết hạn. Trả về thứ ấy (hoặc null).
  const choCo = async (lay, hanMs) => {
    const het = Date.now() + hanMs;
    for (;;) {
      let ra = null;
      try { ra = lay(); } catch (e) { ra = null; }
      if (ra) return ra;
      if (Date.now() > het) return null;
      await cho(NHIP_MS);
    }
  };

  const hien = (el) => !!(el && el.offsetParent !== null);

  // ── Mở phần mô tả: nút "Bản chép lời" nằm sau "...more" (tiếng Nhật: "...もっと見る") ──
  let daCuon = false, daBamMo = false;
  const moMoTa = () => {
    // YouTube dựng LƯỜI phần dưới màn hình: mô tả và khối "Bản chép lời" có thể chưa được
    // dựng chừng nào chưa cuộn tới. Cuộn một lần tới vùng mô tả trước khi tìm nút.
    const vung = document.querySelector('#description-inline-expander')
      || document.querySelector('ytd-text-inline-expander')
      || document.querySelector('ytd-watch-metadata');
    if (vung && !daCuon) {
      try { vung.scrollIntoView({ block: 'center' }); } catch (e) { /* bỏ qua */ }
      daCuon = true;
    }
    // Có thể có HAI phần tử `#expand` (đo thật: `any #expand: 2`) — lấy cái ĐANG HIỆN.
    const cac = Array.from(document.querySelectorAll(
      '#description-inline-expander #expand, ytd-text-inline-expander #expand, tp-yt-paper-button#expand'));
    const mo = cac.find(hien);
    if (mo) { mo.click(); if (!daBamMo) { daBamMo = true; noi(`${MA}: đã bấm mở mô tả`); } return true; }
    return false;
  };

  const nutTranscript = () => {
    const khoi = document.querySelector('ytd-video-description-transcript-section-renderer');
    if (!khoi) return null;
    // Đo thật 22/09/2026 (soi DOM qua DevTools, phiên TL2-T7, video wtNORy6MxLQ): trong khối
    // này YouTube đặt HAI nút "Hiện bản chép lời" — nút đầu theo thứ tự DOM bị ẨN
    // (offsetParent null), nút sau mới hiện. `querySelector` lấy nút đầu → ẩn → hàm này
    // trả null suốt 12 giây → cả sáu video một lượt bị ghi nhầm "không có bảng phụ đề".
    // Phải chọn nút ĐANG HIỆN đầu tiên, không phải nút đầu tiên.
    const cac = Array.from(khoi.querySelectorAll('button, yt-button-shape button, tp-yt-paper-button'));
    return cac.find(hien) || null;
  };

  const bangTranscript = () => {
    const panel = document.querySelector(
      'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"]');
    // `target-id` có mặt cả khi panel còn ẩn — phải xem nó đã HIỆN chưa, không thì ta gom
    // một bảng rỗng rồi kết luận sai là "video không có phụ đề".
    if (panel && panel.querySelector('ytd-transcript-segment-renderer')) return panel;
    const lui = document.querySelector('ytd-transcript-renderer');
    return (lui && lui.querySelector('ytd-transcript-segment-renderer')) ? lui : null;
  };

  const soDoan = () => document.querySelectorAll('ytd-transcript-segment-renderer').length;

  // Bảng nạp dần (YouTube dựng từng đoạn): chờ tới khi SỐ ĐOẠN đứng yên hai nhịp liền,
  // chứ không chờ một khoảng cứng — video 3 phút và video 40 phút nạp lâu khác nhau hẳn.
  const choDoanDungYen = async () => {
    const het = Date.now() + CHO_DOAN_MS;
    let truoc = -1, yen = 0;
    for (;;) {
      const nay = soDoan();
      yen = (nay > 0 && nay === truoc) ? yen + 1 : 0;
      truoc = nay;
      if (yen >= 2 || Date.now() > het) return nay;
      await cho(NHIP_MS);
    }
  };

  const _BO_MOC_GIO = /^\d{1,2}:\d{2}(?::\d{2})?\s*/;

  const gomChu = () => {
    const ra = [];
    document.querySelectorAll('ytd-transcript-segment-renderer').forEach((d) => {
      const o = d.querySelector('.segment-text, yt-formatted-string.segment-text');
      let t = ((o ? (o.innerText || o.textContent) : d.innerText) || '').trim();
      // Không có `.segment-text` (YouTube đổi lớp) thì `innerText` của cả đoạn mang theo
      // mốc giờ ở đầu ("0:12 …") — cắt nó ra, đừng để mốc giờ lẫn vào kịch bản.
      if (!o) t = t.replace(_BO_MOC_GIO, '').trim();
      // Bỏ dòng trùng LIỀN KỀ: bản phụ đề máy nghe đôi khi lặp đoạn trước.
      if (t && ra[ra.length - 1] !== t) ra.push(t);
    });
    return ra.join(' ').replace(/\s+/g, ' ').trim();
  };

  const tieuDe = () => {
    const h = document.querySelector('ytd-watch-metadata h1 yt-formatted-string, h1.ytd-watch-metadata');
    return ((h && (h.innerText || h.textContent)) || document.title || '').trim().slice(0, 300);
  };

  const daiGiay = () => {
    const v = document.querySelector('video');
    const d = v && Number(v.duration);
    return (d && isFinite(d) && d > 0) ? Math.round(d) : 0;
  };

  // ═══ ĐƯỜNG THẲNG: đọc link phụ đề trong dữ liệu player, tải thẳng — KHÔNG bấm gì ═══
  //
  // 22/09/2026, sau bốn lượt bấm-mở-bảng đều trượt: trang xem đã CHỨA SẴN danh sách phụ đề
  // trong `ytInitialPlayerResponse.captions.playerCaptionsTracklistRenderer.captionTracks`
  // (kể cả phụ đề tự động, `kind: "asr"`), mỗi mục một `baseUrl`. Tải `baseUrl&fmt=json3`
  // từ trong trang — cùng phiên, cùng cookie, cùng IP của trình duyệt kênh — là có chữ.
  // Không phụ thuộc nút nào, thẻ nào, thứ tự dựng nào của YouTube. Đường bấm-bảng bên
  // dưới chỉ còn là dự phòng khi dữ liệu player không có phụ đề.
  const docPlayer = () => {
    for (const s of Array.from(document.scripts)) {
      const t = s.textContent || '';
      const i = t.indexOf('ytInitialPlayerResponse');
      if (i < 0) continue;
      const j = t.indexOf('{', i);
      if (j < 0) continue;
      // Cắt JSON bằng đếm ngoặc (chuỗi có thể chứa `}`), không dùng regex.
      let d = 0, trongChuoi = false, thoat = false;
      for (let k = j; k < t.length; k++) {
        const c = t[k];
        if (trongChuoi) { if (thoat) thoat = false; else if (c === '\\') thoat = true; else if (c === '"') trongChuoi = false; continue; }
        if (c === '"') trongChuoi = true;
        else if (c === '{') d++;
        else if (c === '}') { d--; if (d === 0) { try { return JSON.parse(t.slice(j, k + 1)); } catch (e) { return null; } } }
      }
    }
    return null;
  };

  const chonTrack = (pr) => {
    const cac = (((pr || {}).captions || {}).playerCaptionsTracklistRenderer || {}).captionTracks || [];
    if (!cac.length) return null;
    const ja = cac.filter((c) => String(c.languageCode || '').startsWith('ja'));
    const uuTien = ja.find((c) => c.kind !== 'asr') || ja.find((c) => c.kind === 'asr');
    return uuTien || cac.find((c) => c.kind !== 'asr') || cac[0];
  };

  const taiPhuDe = async (track) => {
    const url = String(track.baseUrl || '');
    if (!url) return '';
    const r = await fetch(url + (url.includes('fmt=') ? '' : '&fmt=json3'), { credentials: 'include' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    const ra = [];
    for (const ev of (j.events || [])) {
      const dong = (ev.segs || []).map((sg) => sg.utf8 || '').join('').replace(/\s+/g, ' ').trim();
      if (dong && ra[ra.length - 1] !== dong) ra.push(dong);
    }
    return ra.join(' ').replace(/\s+/g, ' ').trim();
  };

  // ── Một video: đường thẳng trước, bấm bảng sau; báo về background (nó lo POST + video kế) ──
  (async () => {
    if (!(await duocKich())) return;
    let text = '', loi = '';
    try {
      const pr = docPlayer();
      const track = chonTrack(pr);
      if (track) {
        try {
          text = await taiPhuDe(track);
          await noi(`${MA}: đường thẳng — ${track.languageCode}${track.kind === 'asr' ? '/tự động' : ''}: ${text.length} ký tự`);
        } catch (e) {
          await noi(`${MA}: đường thẳng lỗi (${(e && e.message) || e}) — thử bấm bảng`);
        }
      } else {
        await noi(`${MA}: player ${pr ? 'không có mục phụ đề' : 'không đọc được'} — thử bấm bảng`);
      }
    } catch (e) { /* rơi xuống đường bấm bảng */ }
    if (!text) try {
      // Chờ khối "Bản chép lời" — mở mô tả trước, vì trước khi mở thì khối ấy chưa có
      // trong DOM. Bấm mở nhiều lần không hại gì (nút thành "...ít hơn" thì thôi).
      const nut = await choCo(() => {
        const n = nutTranscript();
        if (n) return n;
        moMoTa();
        return null;
      }, CHO_MO_TA_MS);
      if (!nut) {
        // Nói rõ TRẠNG THÁI DOM lúc bỏ cuộc — hôm 22/09 câu lỗi chung chung này lặp 12 lần mà
        // không phân biệt được "trang chưa dựng" với "YouTube đổi thẻ".
        const q = (s) => document.querySelector(s);
        const cacMo = Array.from(document.querySelectorAll('#expand'));
        loi = 'không thấy khối "Bản chép lời" trong phần mô tả'
          + ` (metadata=${!!q('ytd-watch-metadata')} · nút-mở=${cacMo.length}/${cacMo.filter(hien).length} hiện`
          + ` · đã-bấm=${daBamMo} · khối=${!!q('ytd-video-description-transcript-section-renderer')})`;
      } else {
        nut.click();
        const bang = await choCo(bangTranscript, CHO_PANEL_MS);
        if (!bang) {
          loi = 'bấm mở nhưng bảng phụ đề không hiện đoạn nào';
        } else {
          await choDoanDungYen();
          text = gomChu();
          if (!text) loi = 'bảng phụ đề mở ra nhưng không đọc được chữ nào';
        }
      }
    } catch (e) {
      loi = 'lỗi khi hút bảng phụ đề: ' + ((e && e.message) || e);
    }
    await noi(`${MA}: ${text ? text.length + ' ký tự' : 'không có bảng phụ đề'}`
              + (loi ? ` (${loi})` : ''));
    // KHÔNG gửi `ngon_ngu`: bảng phụ đề chỉ cho một NHÃN đã dịch theo giao diện
    // ("日本語 (自動生成)"), không cho mã ngôn ngữ. Một mã đoán sai còn tệ hơn một ô
    // trống — khâu remake dùng ngôn ngữ khai trong `kenh.yaml`, không dùng ô này.
    await goi({
      type: 'loi_thoai', video_id: MA, text, tieu_de: tieuDe(),
      dai_giay: daiGiay(), khong_co: !text, loi,
    });
  })();
})();
