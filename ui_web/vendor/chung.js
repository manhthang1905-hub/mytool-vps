/* Thư viện dùng chung 3 trang Trung tâm chỉ huy (không phụ thuộc gì ngoài trình duyệt). */
(function () {
  "use strict";
  const MT = {};
  const GIAM = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  MT.giamChuyenDong = GIAM;

  /* ---------- định dạng ---------- */
  MT.esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  MT.so = (n, le) => (Number(n) || 0).toLocaleString("vi-VN", {maximumFractionDigits: le == null ? 0 : le});
  MT.fmt = n => {
    n = Number(n) || 0; const a = Math.abs(n);
    if (a >= 1e9) return MT.so(n / 1e9, 2) + " tỉ";
    if (a >= 1e6) return MT.so(n / 1e6, a >= 1e8 ? 0 : 1) + " tr";
    if (a >= 1e4) return MT.so(n / 1e3, a >= 1e5 ? 0 : 1) + " N";
    return MT.so(n, a < 10 && n % 1 ? 1 : 0);
  };
  MT.pc = (n, le) => {
    n = Number(n) || 0;
    if (le == null) le = n === 0 ? 0 : (Math.abs(n) < 0.1 ? 3 : Math.abs(n) < 10 ? 2 : 1);
    return MT.so(n, le) + "%";
  };
  MT.bam = s => { let h = 2166136261; for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  MT.kep = (v, a, b) => Math.max(a, Math.min(b, v));

  /* Mã kênh rút gọn: bỏ đoạn chung của mọi mã (VD «-T7»), giữ phần phân biệt. TL4-T7-K2 → TL4·K2 */
  MT.boMaNgan = dsMa => {
    const tach = dsMa.map(m => String(m).split("-"));
    const chung = new Set();
    if (tach.length > 1) {
      const dem = {};
      tach.forEach(t => new Set(t.slice(1)).forEach(p => { dem[p] = (dem[p] || 0) + 1; }));
      Object.keys(dem).forEach(p => { if (dem[p] === tach.length) chung.add(p); });
    }
    const ra = {};
    dsMa.forEach((m, i) => { const g = tach[i].filter((p, j) => j === 0 || !chung.has(p)); ra[m] = g.join("·") || m; });
    return m => ra[m] || String(m || "");
  };

  /* ---------- biểu tượng (SVG sprite nội tuyến, nét kiểu lucide) ---------- */
  const IC = {
    swords: '<path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="m13 19 6-6"/><path d="m16 16 4 4"/><path d="m19 21 2-2"/><path d="M14.5 6.5 18 3h3v3l-3.5 3.5"/><path d="m5 14 4 4"/><path d="m7 17-3 3"/><path d="m3 19 2 2"/>',
    sword: '<path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="m13 19 6-6"/><path d="m16 16 4 4"/><path d="m19 21 2-2"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    castle: '<path d="M3 21h18"/><path d="M5 21V8h2.5V5H10v3h4V5h2.5v3H19v13"/><path d="M10 21v-4a2 2 0 0 1 4 0v4"/><path d="M5 12h14"/>',
    crown: '<path d="m2 6 4 11h12l4-11-6 5-4-7-4 7z"/><path d="M6 21h12"/>',
    trophy: '<path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3"/><path d="M7 5H4v2a3 3 0 0 0 3 3"/>',
    map: '<path d="M14.1 5.55a2 2 0 0 0 1.8 0l3.65-1.83A1 1 0 0 1 21 4.62v12.76a1 1 0 0 1-.55.9l-4.56 2.27a2 2 0 0 1-1.78 0l-4.22-2.1a2 2 0 0 0-1.78 0l-3.66 1.82A1 1 0 0 1 3 19.38V6.62a1 1 0 0 1 .55-.9l4.56-2.27a2 2 0 0 1 1.78 0z"/><path d="M15 5.76v15"/><path d="M9 3.24v15"/>',
    factory: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>',
    brain: '<path d="M12 5a3 3 0 1 0-6 .13 4 4 0 0 0-2.52 5.77 4 4 0 0 0 .55 6.59A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 6 .13 4 4 0 0 1 2.52 5.77 4 4 0 0 1-.55 6.59A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M12 5v13"/>',
    eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    star: '<path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    zap: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
    terminal: '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>',
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/><path d="M6.5 17A2.5 2.5 0 0 0 4 19.5 2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    drive: '<path d="M22 12H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M6 16h.01"/><path d="M10 16h.01"/>',
    cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    pulse: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 16 2 2 4-4"/>',
    trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    left: '<path d="m15 18-6-6 6-6"/>',
    box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    file: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z"/><path d="M14 2v6h6"/><path d="M16 13H8M16 17H8M10 9H8"/>',
    mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    captions: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 15h4M15 15h2M7 11h2M13 11h4"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/>',
    film: '<rect x="2" y="2" width="20" height="20" rx="2.18"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/>',
    frame: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="m8 15 3-3 2 2 3-4 3 5"/>',
    scissors: '<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/><path d="M20 4 8.12 15.88"/><circle cx="6" cy="18" r="3"/><path d="M14.8 14.8 20 20"/>',
    bow: '<path d="M5 3c9 2 14 7 16 16"/><path d="M5 3 21 19"/><path d="M3 21l6-6"/><path d="M3 17v4h4"/>',
    spear: '<path d="M21 3 9 15"/><path d="M21 3h-6l3 3z"/><path d="m3 21 4-4"/><path d="M7 13l4 4"/>',
    axe: '<path d="m14 12-8.5 8.5a2.12 2.12 0 1 1-3-3L11 9"/><path d="M15 13 9 7l4-4 6 6h3a8 8 0 0 1-7 7z"/>',
    wand: '<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4M19 14v4M10 2v2M7 8H3M21 16h-4M11 3H9"/>',
    hammer: '<path d="m15 12-8.5 8.5a2.12 2.12 0 1 1-3-3L12 9"/><path d="M17.64 15 22 10.64"/><path d="m20.91 11.7-1.25-1.25a1.6 1.6 0 0 1 0-2.25l.4-.4-3.8-3.8a4.8 4.8 0 0 0-6.8 0l-.4.4 3.8 3.8a1.6 1.6 0 0 1 0 2.25l1.25 1.25"/>',
    medal: '<path d="M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15"/><path d="M11 12 5.12 2.2M13 12l5.88-9.8M8 7h8"/><circle cx="12" cy="17" r="5"/><path d="M12 18v-2h-.5"/>',
    lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    radar: '<path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/><path d="M4 6h.01"/><path d="M2.29 9.62A10 10 0 1 0 21.31 8.35"/><path d="M16.24 7.76A6 6 0 1 0 8.23 16.67"/><path d="M12 18h.01"/><path d="M17.99 11.66A6 6 0 0 1 15.77 16.67"/><circle cx="12" cy="12" r="2"/><path d="m13.41 10.59 5.66-5.66"/>',
    scroll: '<path d="M8 21h12a2 2 0 0 0 2-2v-2H10v2a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v3h4"/><path d="M19 17V5a2 2 0 0 0-2-2H4"/><path d="M15 8h-5M15 12h-5"/>',
    layers: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    sparkles: '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5A2 2 0 0 0 15.5 9.94l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>',
    yen: '<circle cx="12" cy="12" r="10"/><path d="m8 7 4 5 4-5M12 12v6M9 13h6M9 16h6"/>',
    play: '<path d="M6 4v16l14-8z"/>',
    truck: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
    message: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    hourglass: '<path d="M5 22h14M5 2h14"/><path d="M17 22v-4.17a2 2 0 0 0-.59-1.42L12 12l-4.41 4.41A2 2 0 0 0 7 17.83V22"/><path d="M7 2v4.17a2 2 0 0 0 .59 1.42L12 12l4.41-4.41A2 2 0 0 0 17 6.17V2"/>',
  };
  MT.ic = (ten, lop) => `<svg class="ic ${lop || ""}" viewBox="0 0 24 24" aria-hidden="true">${IC[ten] || ""}</svg>`;
  MT.icTho = ten => IC[ten] || "";
  MT.LOP_QUAN = ["sword", "bow", "spear", "axe", "wand", "hammer", "shield"];
  MT.TEN_LOP = {sword: "Kiếm sĩ", bow: "Cung thủ", spear: "Thương binh", axe: "Chiến binh rìu", wand: "Pháp sư", hammer: "Thợ rèn", shield: "Hộ vệ"};

  /* ---------- sparkline ---------- */
  MT.spark = (ys, mau) => {
    mau = mau || "var(--ta)";
    const W = 120, H = 34;
    if (!ys.length) return "";
    const id = "g" + MT.bam(ys.join(",") + mau) % 1e7;
    if (ys.length === 1) {
      return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2="${W}" y1="${H - 8}" y2="${H - 8}" stroke="${mau}" stroke-opacity=".35" stroke-dasharray="3 4"/><circle cx="${W - 4}" cy="${H - 8}" r="3" fill="${mau}"/></svg>`;
    }
    let lo = Math.min(...ys), hi = Math.max(...ys); if (hi === lo) { hi += 1; lo -= 1; }
    const X = i => 2 + (W - 6) * i / (ys.length - 1), Y = v => 3 + (H - 8) * (1 - (v - lo) / (hi - lo));
    const d = ys.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join("");
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mau}" stop-opacity=".35"/><stop offset="1" stop-color="${mau}" stop-opacity="0"/></linearGradient></defs>
      <path d="${d}L${X(ys.length - 1).toFixed(1)} ${H}L${X(0).toFixed(1)} ${H}Z" fill="url(#${id})"/><path d="${d}" fill="none" stroke="${mau}" stroke-width="1.8" vector-effect="non-scaling-stroke"/>
      <circle cx="${X(ys.length - 1).toFixed(1)}" cy="${Y(ys[ys.length - 1]).toFixed(1)}" r="2.6" fill="${mau}"/></svg>`;
  };

  /* ---------- vòng tiến độ ---------- */
  MT.vong = (phan, co, mau, chu, phu, day) => {
    co = co || 64; day = day || 6; phan = MT.kep(Number(phan) || 0, 0, 1);
    const r = (co - day) / 2, cv = 2 * Math.PI * r;
    return `<svg width="${co}" height="${co}" viewBox="0 0 ${co} ${co}" class="vong" aria-hidden="true">
      <circle cx="${co / 2}" cy="${co / 2}" r="${r}" fill="none" stroke="rgba(125,160,215,.13)" stroke-width="${day}"/>
      <circle cx="${co / 2}" cy="${co / 2}" r="${r}" fill="none" stroke="${mau}" stroke-width="${day}" stroke-linecap="round"
        stroke-dasharray="${(cv * phan).toFixed(2)} ${cv.toFixed(2)}" transform="rotate(-90 ${co / 2} ${co / 2})" style="filter:drop-shadow(0 0 4px ${mau})"/>
      ${chu ? `<text x="50%" y="${phu ? "47%" : "53%"}" text-anchor="middle" dominant-baseline="middle" fill="var(--chu)" style="font:700 ${co > 70 ? 16 : 12.5}px var(--f-hud)">${chu}</text>` : ""}
      ${phu ? `<text x="50%" y="68%" text-anchor="middle" dominant-baseline="middle" fill="var(--mo)" style="font:600 8.5px var(--f-hud);letter-spacing:.08em">${phu}</text>` : ""}</svg>`;
  };

  /* ---------- tooltip ---------- */
  let tipEl = null;
  MT.tip = (html, e) => {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; document.body.appendChild(tipEl); }
    tipEl.innerHTML = html; tipEl.classList.add("hien");
    MT.tipDoi(e);
  };
  MT.tipDoi = e => {
    if (!tipEl || !e) return;
    const w = tipEl.offsetWidth, h = tipEl.offsetHeight, vw = innerWidth, vh = innerHeight;
    let x = e.clientX + 16, y = e.clientY + 16;
    if (x + w > vw - 8) x = e.clientX - w - 14; if (x < 8) x = 8;
    if (y + h > vh - 8) y = e.clientY - h - 14; if (y < 8) y = 8;
    tipEl.style.left = x + "px"; tipEl.style.top = y + "px";
  };
  MT.tipAn = () => { if (tipEl) tipEl.classList.remove("hien"); };

  /* ---------- ngăn kéo bên phải ---------- */
  let ngan = null, che = null;
  MT.moNgan = (tieuDe, phuDe, than) => {
    if (!ngan) {
      che = document.createElement("div"); che.className = "man-che"; document.body.appendChild(che);
      ngan = document.createElement("aside"); ngan.className = "ngan-keo"; ngan.setAttribute("role", "dialog"); ngan.setAttribute("aria-modal", "true");
      document.body.appendChild(ngan);
      che.addEventListener("click", MT.dongNgan);
      document.addEventListener("keydown", e => { if (e.key === "Escape") MT.dongNgan(); });
    }
    ngan.innerHTML = `<div class="dau"><div style="min-width:0">${phuDe || ""}<h3>${tieuDe}</h3></div><button class="dong-x" aria-label="Đóng">${MT.ic("x")}</button></div><div class="dong-cuon">${than}</div>`;
    ngan.querySelector(".dong-x").addEventListener("click", MT.dongNgan);
    requestAnimationFrame(() => { che.classList.add("hien"); ngan.classList.add("hien"); });
    ngan.scrollTop = 0;
    return ngan;
  };
  MT.dongNgan = () => { if (ngan) { ngan.classList.remove("hien"); che.classList.remove("hien"); } if (MT.khiDongNgan) MT.khiDongNgan(); };

  /* ---------- biểu đồ vùng (chuỗi theo ngày) ---------- */
  // ds: [{ngay:"YYYY-MM-DD", v:số, ...}], o: {mau, dang(v), cao, nguong:{v,chu}, coDinh:[lo,hi], muc_tieu_ngay, ten, phu(p)}
  MT.bieuDoVung = (hop, ds, o) => {
    o = o || {}; const mau = o.mau || "var(--ta)", dang = o.dang || MT.fmt, H = o.cao || 170;
    const W = Math.max(260, hop.clientWidth || 400), L = 6, R = 10, T = 14, B = 22;
    const id = "v" + MT.bam(JSON.stringify(ds) + mau) % 1e8;
    if (!ds.length) { hop.innerHTML = `<div class="trong" style="padding:24px 0">${o.rong || "Chưa có lịch sử — mỗi ngày ghi một điểm."}</div>`; return; }
    const ys = ds.map(p => Number(p.v) || 0);
    let lo = o.coDinh ? o.coDinh[0] : Math.min(...ys), hi = o.coDinh ? o.coDinh[1] : Math.max(...ys);
    if (!o.coDinh) { const pad = (hi - lo) * .18 || Math.abs(hi) * .2 || 1; lo = Math.max(o.am ? -Infinity : 0, lo - pad); hi = hi + pad; }
    const n = ds.length, mucTieu = o.mucTieu || 7;
    const X = i => n === 1 ? L + (W - L - R) * 0.06 : L + (W - L - R) * i / (n - 1);
    const Y = v => T + (H - T - B) * (1 - (v - lo) / (hi - lo || 1));
    const ke = [0, .5, 1].map(f => lo + (hi - lo) * f);
    let s = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="${MT.esc(o.ten || "biểu đồ")}"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mau}" stop-opacity=".32"/><stop offset="1" stop-color="${mau}" stop-opacity="0"/></linearGradient></defs>`;
    s += ke.map(v => `<line class="ke" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="truc" x="${W - R}" y="${(Y(v) - 4).toFixed(1)}" text-anchor="end">${dang(v)}</text>`).join("");
    if (o.nguong) s += `<line x1="${L}" x2="${W - R}" y1="${Y(o.nguong.v)}" y2="${Y(o.nguong.v)}" stroke="var(--tranh)" stroke-dasharray="5 5" stroke-opacity=".8"/><text class="truc" x="${L + 2}" y="${Y(o.nguong.v) - 5}" fill="var(--tranh)" style="fill:var(--tranh)">${MT.esc(o.nguong.chu)}</text>`;
    if (n === 1) {
      const x = X(0), y = Y(ys[0]);
      s += `<line x1="${x}" x2="${W - R}" y1="${y}" y2="${y}" stroke="${mau}" stroke-opacity=".45" stroke-dasharray="2 6" stroke-width="2"/>`;
      s += `<rect x="${x}" y="${y}" width="${W - R - x}" height="${H - B - y}" fill="url(#${id})" opacity=".55"/>`;
      s += `<circle cx="${x}" cy="${y}" r="9" fill="${mau}" opacity=".18"/><circle cx="${x}" cy="${y}" r="4.5" fill="${mau}"/>`;
      s += `<text class="truc" x="${x}" y="${H - 6}">${ds[0].ngay.slice(8, 10)}/${ds[0].ngay.slice(5, 7)}</text>`;
      s += `<text class="chua-du" x="${(x + W - R) / 2 + 20}" y="${Math.min(H - B - 14, y + 30)}" text-anchor="middle">Ngày 1/${mucTieu} — xu hướng hiện từ ngày thứ 2</text>`;
    } else {
      const d = ys.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join("");
      s += `<path d="${d}L${X(n - 1).toFixed(1)} ${H - B}L${X(0).toFixed(1)} ${H - B}Z" fill="url(#${id})"/>`;
      s += `<path d="${d}" fill="none" stroke="${mau}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" style="filter:drop-shadow(0 0 5px ${mau})"/>`;
      const nhan = n <= 8 ? ds.map((p, i) => i) : [0, Math.floor((n - 1) / 2), n - 1];
      s += nhan.map(i => `<text class="truc" x="${X(i).toFixed(1)}" y="${H - 6}" text-anchor="${i === 0 ? "start" : i === n - 1 ? "end" : "middle"}">${ds[i].ngay.slice(8, 10)}/${ds[i].ngay.slice(5, 7)}</text>`).join("");
      s += `<circle cx="${X(n - 1)}" cy="${Y(ys[n - 1])}" r="4" fill="${mau}"/>`;
      s += `<line class="tro-doc" x1="0" x2="0" y1="${T}" y2="${H - B}" stroke="var(--vien2)" opacity="0"/><circle class="tro-cham" r="4.5" fill="${mau}" stroke="#06101c" stroke-width="2" opacity="0"/>`;
      s += `<rect class="bat" x="0" y="0" width="${W}" height="${H}" fill="transparent"/>`;
    }
    hop.innerHTML = s + "</svg>";
    if (n > 1) {
      const svg = hop.querySelector("svg"), doc = svg.querySelector(".tro-doc"), ch = svg.querySelector(".tro-cham");
      svg.querySelector(".bat").addEventListener("mousemove", e => {
        const r = svg.getBoundingClientRect(), x = (e.clientX - r.left) * W / r.width;
        const i = MT.kep(Math.round((x - L) / ((W - L - R) / (n - 1))), 0, n - 1);
        doc.setAttribute("x1", X(i)); doc.setAttribute("x2", X(i)); doc.setAttribute("opacity", 1);
        ch.setAttribute("cx", X(i)); ch.setAttribute("cy", Y(ys[i])); ch.setAttribute("opacity", 1);
        MT.tip(`<div class="mo nho">${MT.esc(ds[i].ngay)}</div><div style="font:700 18px var(--f-hud)">${dang(ys[i])}</div>${o.phu ? o.phu(ds[i]) : ""}`, e);
      });
      svg.querySelector(".bat").addEventListener("mouseleave", () => { doc.setAttribute("opacity", 0); ch.setAttribute("opacity", 0); MT.tipAn(); });
    }
  };

  /* ---------- trạng thái sống + tải dữ liệu ---------- */
  MT.song = (luc, loi) => {
    const c = document.getElementById("cham-song"), t = document.getElementById("chu-song");
    if (!c || !t) return;
    if (loi) { c.className = "cham-song loi"; t.textContent = "mất kết nối: " + loi; return; }
    const d = luc ? new Date(String(luc).replace(" ", "T")) : null;
    const phut = d && !isNaN(d) ? Math.round((Date.now() - d) / 60000) : null;
    c.className = "cham-song" + (phut != null && phut > 30 ? " cu" : "");
    t.textContent = `số liệu ${luc || "?"}` + (phut != null ? ` · ${phut < 1 ? "vừa xong" : phut < 60 ? phut + " phút trước" : Math.round(phut / 60) + " giờ trước"}` : "");
  };
  MT.taiJSON = async url => {
    const r = await fetch(url, {cache: "no-store"});
    const d = await r.json();
    if (!r.ok) throw new Error((d && d.loi) || ("HTTP " + r.status));
    return d;
  };
  MT.lamMoi = (ham, ms) => {      // làm mới định kỳ, tạm dừng khi tab ẩn (tiết kiệm CPU máy VPS)
    let hen = null;
    const chay = () => { clearTimeout(hen); if (!document.hidden) ham(); hen = setTimeout(chay, ms); };
    document.addEventListener("visibilitychange", () => { if (!document.hidden) chay(); });
    hen = setTimeout(chay, ms);
  };
  MT.doiCo = (ham, ms) => { let t; return () => { clearTimeout(t); t = setTimeout(ham, ms || 150); }; };

  /* ---------- thông báo nhỏ (toast) ---------- */
  let khayToast = null;
  MT.toast = (html, ms) => {
    if (!khayToast) { khayToast = document.createElement("div"); khayToast.className = "khay-toast"; khayToast.setAttribute("aria-live", "polite"); document.body.appendChild(khayToast); }
    const t = document.createElement("div"); t.className = "toast"; t.innerHTML = html;
    t.addEventListener("click", () => t.remove());
    khayToast.appendChild(t);
    while (khayToast.children.length > 4) khayToast.firstChild.remove();
    setTimeout(() => { t.classList.add("di"); setTimeout(() => t.remove(), 400); }, ms || 6500);
  };

  /* ---------- khoe: lên cấp / thành tựu (một lần, bỏ qua được) ---------- */
  MT.khoe = ds => {
    if (!ds || !ds.length) return;
    const lop = document.createElement("div"); lop.className = "khoe"; lop.setAttribute("role", "dialog"); lop.setAttribute("aria-label", "Thành tích mới");
    const d = ds[0];
    lop.innerHTML = `<canvas class="phao-giay" aria-hidden="true"></canvas><div class="the-khoe"><div class="khoe-nhan">${MT.esc(d.nhan)}</div>
      <div class="khoe-huy">${MT.ic(d.ic)}</div><div class="khoe-tieu">${MT.esc(d.tieu)}</div><div class="khoe-phu">${MT.esc(d.phu || "")}</div>
      ${ds.length > 1 ? `<div class="khoe-them">${ds.slice(1, 5).map(x => `<span class="chip vang">${MT.ic(x.ic)}${MT.esc(x.tieu)}</span>`).join("")}${ds.length > 5 ? ` <span class="chip">+${ds.length - 5}</span>` : ""}</div>` : ""}
      <button class="nut on">Tiếp tục</button></div>`;
    document.body.appendChild(lop);
    const dong = () => { lop.classList.add("di"); document.removeEventListener("keydown", phim); setTimeout(() => lop.remove(), 300); };
    const phim = e => { if (e.key === "Escape" || e.key === "Enter" || e.key === " ") { e.preventDefault(); dong(); } };
    lop.addEventListener("click", dong); document.addEventListener("keydown", phim);
    lop.querySelector("button").focus();
    if (GIAM) return;
    const cv = lop.querySelector("canvas"), cx = cv.getContext("2d"), W = cv.width = innerWidth, H = cv.height = innerHeight;
    const MAU = ["#2ee6c5", "#fbbf24", "#a78bfa", "#f472b6", "#60a5fa", "#fde68a"];
    const hat = Array.from({length: 140}, (_, i) => ({x: W / 2 + (Math.random() - .5) * 120, y: H * .42, vx: (Math.random() - .5) * 13, vy: -Math.random() * 13 - 4,
      r: 3 + Math.random() * 4, a: Math.random() * 6.28, va: (Math.random() - .5) * .3, m: MAU[i % MAU.length]}));
    const bd = performance.now();
    const khung = t => {
      const tg = t - bd; if (tg > 2200 || !lop.isConnected) { cx.clearRect(0, 0, W, H); return; }
      cx.clearRect(0, 0, W, H); cx.globalAlpha = Math.max(0, 1 - Math.max(0, tg - 1500) / 700);
      for (const p of hat) { p.vy += .32; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.a += p.va;
        cx.save(); cx.translate(p.x, p.y); cx.rotate(p.a); cx.fillStyle = p.m; cx.fillRect(-p.r, -p.r / 2, p.r * 2, p.r); cx.restore(); }
      requestAnimationFrame(khung);
    };
    requestAnimationFrame(khung);
  };

  /* ---------- phím tắt toàn trang: 1/2/3/4 chuyển trang ---------- */
  document.addEventListener("keydown", e => {
    if (e.ctrlKey || e.metaKey || e.altKey || /INPUT|SELECT|TEXTAREA/.test((e.target || {}).tagName || "") || (e.target || {}).isContentEditable) return;
    const di = {"1": "/", "2": "/hau-can", "3": "/nao", "4": "/gioi-thieu"}[e.key];
    if (di && location.pathname !== di) location.href = di;
  });

  window.MT = MT;
})();
