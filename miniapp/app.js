const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); tg.setHeaderColor('#0a0a0b'); tg.setBackgroundColor('#0a0a0b'); }

const ASSETS = [
  { key:'xauusd', emoji:'🟡', name:'XAUUSD', full:'Золото', binance:null, base:2650 },
  { key:'nasdaq', emoji:'📈', name:'NASDAQ', full:'NASDAQ 100', binance:null, base:20500 },
  { key:'sp500', emoji:'📊', name:'S&P 500', full:'S&P 500', binance:null, base:5800 },
  { key:'btc', emoji:'🪙', name:'BTC', full:'Bitcoin', binance:'BTCUSDT', base:67000 },
  { key:'eth', emoji:'💎', name:'ETH', full:'Ethereum', binance:'ETHUSDT', base:3500 },
  { key:'dxy', emoji:'💵', name:'DXY', full:'Dollar Index', binance:null, base:104.5 },
  { key:'oil', emoji:'🛢', name:'OIL', full:'Brent / WTI', binance:null, base:78 },
  { key:'eurusd', emoji:'💶', name:'EURUSD', full:'EUR/USD', binance:null, base:1.085 },
  { key:'gbpusd', emoji:'💷', name:'GBPUSD', full:'GBP/USD', binance:null, base:1.305 },
  { key:'usdjpy', emoji:'💴', name:'USDJPY', full:'USD/JPY', binance:null, base:149.5 },
  { key:'agro', emoji:'🌾', name:'AGRO', full:'Commodities', binance:null, base:580 },
  { key:'tesla', emoji:'🚗', name:'TSLA', full:'Tesla & EV', binance:null, base:250 },
  { key:'ai_tech', emoji:'🤖', name:'NVDA', full:'AI & Chips', binance:null, base:140 },
];

let notifOn = true;
let onlyHigh = false;
let subscribed = Object.fromEntries(ASSETS.map(a => [a.key, true]));
let currentAsset = null;
let chart = null, candleSeries = null, lineSeries = null;
let chartType = 'candles';
let currentTf = '1m';
let priceInterval = null, ws = null;
let candleData = [];
let lastCandle = null;
let allNews = [], newsFilter = 'all', newsTimer = null;
let sessionOpen = null;

function renderAssets() {
  document.getElementById('assets-grid').innerHTML = ASSETS.map(a =>
    `<button onclick="openAsset('${a.key}')" class="card rounded-2xl p-3.5 text-left">
      <div class="text-2xl mb-1.5">${a.emoji}</div>
      <div class="text-sm font-semibold">${a.name}</div>
      <div class="text-[11px] text-zinc-500 mt-0.5">${a.full}</div>
    </button>`
  ).join('');
}

function renderChips() {
  document.getElementById('subscribe-chips').innerHTML = ASSETS.map(a =>
    `<button onclick="toggleSub('${a.key}')" class="px-3 py-1.5 rounded-full text-xs font-medium ${subscribed[a.key] ? 'bg-gold-500/15 text-gold-400 border border-gold-500/40' : 'bg-dark-800 text-zinc-400 border border-white/5'}">
      ${a.emoji} ${a.name}
    </button>`
  ).join('');
}

function switchTab(tab) {
  ['home','news','calendar','settings'].forEach(t => {
    document.getElementById('view-' + t).classList.toggle('hidden', t !== tab);
    document.getElementById('tab-' + t).className = t === tab
      ? 'tab-active flex-1 py-2 rounded-xl text-xs transition-all'
      : 'flex-1 py-2 rounded-xl text-xs text-zinc-400 transition-all';
  });
  if (tg) tg.HapticFeedback?.impactOccurred('light');
  if (tab === 'news') {
    loadNews();
    if (newsTimer) clearInterval(newsTimer);
    newsTimer = setInterval(() => loadNews(), 45000);
  } else if (newsTimer) {
    clearInterval(newsTimer);
    newsTimer = null;
  }
}

function updateNotifUI() {
  const btn = document.getElementById('btn-notif');
  if (btn) {
    btn.textContent = notifOn ? '🔔 Вкл' : '🔇 Выкл';
    btn.className = notifOn
      ? 'px-3 py-1.5 rounded-full text-xs font-medium bg-dark-800 border border-white/10 text-zinc-300'
      : 'px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/20 border border-red-500/30 text-red-400';
  }
  const home = document.getElementById('home-notif-status');
  if (home) home.textContent = 'Уведомления: ' + (notifOn ? 'включены' : 'выключены');
  ['toggle-news-notif', 'toggle-settings-notif'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const knob = el.querySelector('span');
    if (notifOn) {
      el.classList.add('bg-accent-green');
      el.classList.remove('bg-dark-600');
      if (knob) knob.style.transform = 'translateX(20px)';
    } else {
      el.classList.remove('bg-accent-green');
      el.classList.add('bg-dark-600');
      if (knob) knob.style.transform = 'translateX(0)';
    }
  });
}

function toggleNotif() {
  notifOn = !notifOn;
  updateNotifUI();
  if (tg) tg.HapticFeedback?.notificationOccurred(notifOn ? 'success' : 'warning');
  try { localStorage.setItem('macro_notif', notifOn ? '1' : '0'); } catch(e) {}
}

function toggleHigh() {
  onlyHigh = !onlyHigh;
  const t = document.getElementById('toggle-high');
  if (!t) return;
  const k = t.querySelector('span');
  if (onlyHigh) {
    t.classList.add('bg-gold-500');
    t.classList.remove('bg-dark-600');
    if (k) k.style.transform = 'translateX(20px)';
  } else {
    t.classList.remove('bg-gold-500');
    t.classList.add('bg-dark-600');
    if (k) k.style.transform = 'translateX(0)';
  }
}

function toggleSub(key) {
  subscribed[key] = !subscribed[key];
  renderChips();
}

async function loadNews(manual) {
  const list = document.getElementById('news-list');
  if (!list) return;
  if (manual) list.innerHTML = '<p class="text-sm text-zinc-500 text-center py-6">Обновление…</p>';
  try {
    const res = await fetch('https://pipatlas.com/api/calendar', { cache: 'no-store' });
    const data = await res.json();
    allNews = data.events || [];
    const upd = data.updated ? new Date(data.updated) : new Date();
    const el = document.getElementById('news-updated');
    if (el) el.textContent = 'Обновлено: ' + upd.toLocaleString('ru-RU', { hour:'2-digit', minute:'2-digit', day:'2-digit', month:'2-digit' }) + ' · ' + allNews.length + ' событий';
    renderNews();
  } catch (e) {
    list.innerHTML = '<p class="text-sm text-red-400 text-center py-6">Ошибка загрузки. Нажми Обновить.</p>';
  }
}

function filterNews(level, btn) {
  newsFilter = level;
  document.querySelectorAll('.news-filter').forEach(b => {
    b.className = 'news-filter px-3 py-1 rounded-full text-xs text-zinc-400 bg-dark-800 whitespace-nowrap';
  });
  if (btn) btn.className = 'news-filter tab-active px-3 py-1 rounded-full text-xs whitespace-nowrap';
  renderNews();
}

function impactStars(imp) {
  if (imp === 'High') return '<span class="text-red-400">⭐️⭐️⭐️</span>';
  if (imp === 'Medium') return '<span class="text-gold-400">⭐️⭐️</span>';
  if (imp === 'Holiday') return '<span class="text-zinc-500">🏖</span>';
  return '<span class="text-zinc-500">⭐️</span>';
}

function renderNews() {
  const list = document.getElementById('news-list');
  if (!list) return;
  let items = newsFilter === 'all' ? allNews : allNews.filter(e => e.impact === newsFilter);
  if (!items.length) {
    list.innerHTML = '<p class="text-sm text-zinc-500 text-center py-8">Нет событий</p>';
    return;
  }
  items = [...items].sort((a, b) => new Date(a.date) - new Date(b.date));
  list.innerHTML = items.map(e => {
    const d = new Date(e.date);
    const timeStr = d.toLocaleString('ru-RU', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' });
    return `<div class="card rounded-2xl p-3.5">
      <div class="flex items-center gap-2 mb-1.5">${impactStars(e.impact)}<span class="text-xs font-medium text-zinc-400">${e.currency || ''}</span><span class="ml-auto text-[11px] text-zinc-500">${timeStr}</span></div>
      <p class="text-sm font-semibold leading-snug">${e.name || ''}</p>
      ${e.impact !== 'Holiday' ? `<div class="flex gap-3 mt-2 text-[11px]"><div><span class="text-zinc-500">Actual</span><br><span class="font-mono">${e.actual || '—'}</span></div><div><span class="text-zinc-500">Forecast</span><br><span class="font-mono text-gold-400">${e.forecast || '—'}</span></div><div><span class="text-zinc-500">Prev</span><br><span class="font-mono text-zinc-400">${e.previous || '—'}</span></div></div>` : ''}
    </div>`;
  }).join('');
}

function openAsset(key) {
  currentAsset = ASSETS.find(a => a.key === key);
  if (!currentAsset) return;
  document.getElementById('app-main').classList.add('hidden');
  document.getElementById('app-asset').classList.remove('hidden');
  document.getElementById('asset-emoji').textContent = currentAsset.emoji;
  document.getElementById('asset-symbol').textContent = currentAsset.name;
  document.getElementById('asset-fullname').textContent = currentAsset.full;
  sessionOpen = currentAsset.base;
  if (tg) { tg.BackButton.show(); tg.BackButton.onClick(closeAsset); tg.HapticFeedback?.impactOccurred('medium'); }
  initChart();
  loadChartData();
  startLivePrice();
}

function closeAsset() {
  stopLive();
  if (chart) { chart.remove(); chart = null; candleSeries = null; lineSeries = null; }
  candleData = []; lastCandle = null;
  document.getElementById('app-asset').classList.add('hidden');
  document.getElementById('app-main').classList.remove('hidden');
  if (tg) tg.BackButton.hide();
}

function initChart() {
  const container = document.getElementById('chart-container');
  container.innerHTML = '';
  chart = LightweightCharts.createChart(container, {
    layout: { background: { type: 'solid', color: '#0a0a0b' }, textColor: '#71717a', fontSize: 11 },
    grid: { vertLines: { color: 'rgba(255,255,255,0.03)' }, horzLines: { color: 'rgba(255,255,255,0.03)' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal, vertLine: { color: 'rgba(232,185,35,0.3)', width: 1, style: 2 }, horzLine: { color: 'rgba(232,185,35,0.3)', width: 1, style: 2 } },
    rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)', scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { borderColor: 'rgba(255,255,255,0.06)', timeVisible: true, secondsVisible: false, rightOffset: 5, barSpacing: 8, minBarSpacing: 4 },
    handleScroll: { vertTouchDrag: false },
  });
  candleSeries = chart.addCandlestickSeries({
    upColor: '#34d399', downColor: '#f87171',
    borderUpColor: '#34d399', borderDownColor: '#f87171',
    wickUpColor: '#34d399', wickDownColor: '#f87171',
    borderVisible: true, wickVisible: true, priceLineVisible: true, lastValueVisible: true,
  });
  lineSeries = chart.addLineSeries({ color: '#e8b923', lineWidth: 2, visible: false, lastValueVisible: true, priceLineVisible: true });
  new ResizeObserver(entries => {
    if (entries[0] && chart) {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) chart.applyOptions({ width, height });
    }
  }).observe(container);
}

function tfToSeconds(tf) {
  return { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 }[tf] || 60;
}

function generateCandles(base, count, tfSec) {
  const now = Math.floor(Date.now() / 1000);
  const aligned = Math.floor(now / tfSec) * tfSec;
  const data = [];
  let price = base * (0.985 + Math.random() * 0.03);
  let trend = (Math.random() - 0.5) * 0.0003;
  for (let i = count; i >= 0; i--) {
    const time = aligned - i * tfSec;
    const open = price;
    trend = trend * 0.95 + (Math.random() - 0.5) * 0.0004;
    const bodyMove = open * trend * (0.5 + Math.random());
    const close = open + bodyMove;
    const wickRange = Math.abs(bodyMove) * (0.3 + Math.random() * 1.2) + open * 0.0003;
    const high = Math.max(open, close) + Math.random() * wickRange;
    const low = Math.min(open, close) - Math.random() * wickRange;
    const d = base >= 100 ? 2 : base >= 1 ? 4 : 5;
    data.push({ time, open: +open.toFixed(d), high: +high.toFixed(d), low: +low.toFixed(d), close: +close.toFixed(d) });
    price = close;
  }
  return data;
}

function loadChartData() {
  if (!currentAsset || !chart) return;
  const tfSec = tfToSeconds(currentTf);
  const count = currentTf === '1d' ? 60 : currentTf === '4h' ? 90 : 120;
  candleData = generateCandles(currentAsset.base, count, tfSec);
  lastCandle = { ...candleData[candleData.length - 1] };
  candleSeries.setData(candleData);
  lineSeries.setData(candleData.map(c => ({ time: c.time, value: c.close })));
  const last = lastCandle;
  sessionOpen = candleData[0].open;
  updatePriceUI(last.close, sessionOpen);
  document.getElementById('stat-open').textContent = formatPrice(last.open);
  document.getElementById('stat-high').textContent = formatPrice(last.high);
  document.getElementById('stat-low').textContent = formatPrice(last.low);
  document.getElementById('stat-close').textContent = formatPrice(last.close);
  chart.timeScale().fitContent();
}

function setTf(btn, tf) {
  currentTf = tf;
  document.querySelectorAll('.tf-btn').forEach(b => {
    b.className = 'tf-btn px-2.5 py-1 rounded-lg text-xs text-zinc-400 bg-dark-800 whitespace-nowrap';
  });
  btn.className = 'tf-btn tf-active px-2.5 py-1 rounded-lg text-xs whitespace-nowrap';
  loadChartData();
  if (tg) tg.HapticFeedback?.selectionChanged();
}

function setChartType(type) {
  chartType = type;
  if (type === 'candles') {
    candleSeries.applyOptions({ visible: true });
    lineSeries.applyOptions({ visible: false });
    document.getElementById('btn-candles').className = 'px-3 py-1 rounded-lg text-xs font-medium bg-gold-500 text-dark-950';
    document.getElementById('btn-line').className = 'px-3 py-1 rounded-lg text-xs font-medium bg-dark-800 text-zinc-400';
  } else {
    candleSeries.applyOptions({ visible: false });
    lineSeries.applyOptions({ visible: true });
    document.getElementById('btn-line').className = 'px-3 py-1 rounded-lg text-xs font-medium bg-gold-500 text-dark-950';
    document.getElementById('btn-candles').className = 'px-3 py-1 rounded-lg text-xs font-medium bg-dark-800 text-zinc-400';
  }
  if (tg) tg.HapticFeedback?.selectionChanged();
}

function formatPrice(p) {
  if (p >= 1000) return Number(p).toFixed(1);
  if (p >= 10) return Number(p).toFixed(2);
  if (p >= 1) return Number(p).toFixed(4);
  return Number(p).toFixed(5);
}

function updatePriceUI(price, ref) {
  document.getElementById('asset-price').textContent = formatPrice(price);
  const base = ref || sessionOpen || price;
  const pct = ((price - base) / base * 100);
  const ch = document.getElementById('asset-change');
  ch.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
  ch.className = 'text-xs font-medium ' + (pct >= 0 ? 'price-up' : 'price-down');
}

function startLivePrice() {
  stopLive();
  lastCandle = candleData.length ? { ...candleData[candleData.length - 1] } : null;
  function tick(price) {
    if (!currentAsset || !candleSeries || !lastCandle) return;
    currentAsset.base = price;
    updatePriceUI(price, sessionOpen);
    const tfSec = tfToSeconds(currentTf);
    const now = Math.floor(Date.now() / 1000);
    const candleTime = Math.floor(now / tfSec) * tfSec;
    const decimals = currentAsset.base >= 100 ? 2 : currentAsset.base >= 1 ? 4 : 5;
    if (lastCandle.time !== candleTime) {
      lastCandle = { time: candleTime, open: +price.toFixed(decimals), high: +price.toFixed(decimals), low: +price.toFixed(decimals), close: +price.toFixed(decimals) };
      candleData.push(lastCandle);
    } else {
      lastCandle.close = +price.toFixed(decimals);
      lastCandle.high = +Math.max(lastCandle.high, price).toFixed(decimals);
      lastCandle.low = +Math.min(lastCandle.low, price).toFixed(decimals);
    }
    try {
      candleSeries.update(lastCandle);
      lineSeries.update({ time: lastCandle.time, value: lastCandle.close });
      document.getElementById('stat-open').textContent = formatPrice(lastCandle.open);
      document.getElementById('stat-high').textContent = formatPrice(lastCandle.high);
      document.getElementById('stat-low').textContent = formatPrice(lastCandle.low);
      document.getElementById('stat-close').textContent = formatPrice(lastCandle.close);
    } catch (e) {}
  }
  if (currentAsset.binance) {
    ws = new WebSocket('wss://stream.binance.com:9443/ws/' + currentAsset.binance.toLowerCase() + '@trade');
    ws.onmessage = (ev) => { tick(parseFloat(JSON.parse(ev.data).p)); };
    document.getElementById('live-indicator').textContent = '● Live Binance';
    document.getElementById('live-indicator').className = 'text-[11px] text-accent-green self-center';
  } else {
    document.getElementById('live-indicator').textContent = '● Live';
    document.getElementById('live-indicator').className = 'text-[11px] text-gold-400 self-center';
    priceInterval = setInterval(() => {
      if (!currentAsset) return;
      const vol = currentAsset.base * 0.0004;
      tick(currentAsset.base + (Math.random() - 0.5) * vol * 2);
    }, 500);
  }
}

function stopLive() {
  if (priceInterval) { clearInterval(priceInterval); priceInterval = null; }
  if (ws) { try { ws.close(); } catch(e) {} ws = null; }
}

try {
  const saved = localStorage.getItem('macro_notif');
  if (saved === '0') notifOn = false;
} catch(e) {}
updateNotifUI();
renderAssets();
renderChips();
