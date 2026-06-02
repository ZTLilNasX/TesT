'use strict';

const STOCKS = [
  { symbol: 'AAPL',  name: 'Apple',             sector: 'Technology' },
  { symbol: 'MSFT',  name: 'Microsoft',          sector: 'Technology' },
  { symbol: 'NVDA',  name: 'NVIDIA',             sector: 'Technology' },
  { symbol: 'GOOGL', name: 'Alphabet',           sector: 'Technology' },
  { symbol: 'AMZN',  name: 'Amazon',             sector: 'Technology' },
  { symbol: 'META',  name: 'Meta',               sector: 'Technology' },
  { symbol: 'TSLA',  name: 'Tesla',              sector: 'Technology' },
  { symbol: 'AMD',   name: 'AMD',                sector: 'Technology' },
  { symbol: 'NFLX',  name: 'Netflix',            sector: 'Technology' },
  { symbol: 'ORCL',  name: 'Oracle',             sector: 'Technology' },
  { symbol: 'CRM',   name: 'Salesforce',         sector: 'Technology' },
  { symbol: 'ADBE',  name: 'Adobe',              sector: 'Technology' },
  { symbol: 'UBER',  name: 'Uber',               sector: 'Technology' },
  { symbol: 'INTC',  name: 'Intel',              sector: 'Technology' },
  { symbol: 'JPM',   name: 'JPMorgan',           sector: 'Finance' },
  { symbol: 'V',     name: 'Visa',               sector: 'Finance' },
  { symbol: 'MA',    name: 'Mastercard',         sector: 'Finance' },
  { symbol: 'BAC',   name: 'Bank of America',    sector: 'Finance' },
  { symbol: 'GS',    name: 'Goldman Sachs',      sector: 'Finance' },
  { symbol: 'BRK-B', name: 'Berkshire Hathaway', sector: 'Finance' },
  { symbol: 'LLY',   name: 'Eli Lilly',          sector: 'Healthcare' },
  { symbol: 'JNJ',   name: 'Johnson & Johnson',  sector: 'Healthcare' },
  { symbol: 'UNH',   name: 'UnitedHealth',       sector: 'Healthcare' },
  { symbol: 'PFE',   name: 'Pfizer',             sector: 'Healthcare' },
  { symbol: 'WMT',   name: 'Walmart',            sector: 'Consumer' },
  { symbol: 'COST',  name: 'Costco',             sector: 'Consumer' },
  { symbol: 'MCD',   name: "McDonald's",         sector: 'Consumer' },
  { symbol: 'NKE',   name: 'Nike',               sector: 'Consumer' },
  { symbol: 'KO',    name: 'Coca-Cola',          sector: 'Consumer' },
  { symbol: 'DIS',   name: 'Disney',             sector: 'Consumer' },
  { symbol: 'XOM',   name: 'ExxonMobil',         sector: 'Energy' },
  { symbol: 'CVX',   name: 'Chevron',            sector: 'Energy' },
  { symbol: 'SPY',   name: 'S&P 500 ETF',        sector: 'ETF' },
  { symbol: 'QQQ',   name: 'Nasdaq-100 ETF',     sector: 'ETF' },
  { symbol: 'DIA',   name: 'Dow Jones ETF',      sector: 'ETF' },
  { symbol: 'VTI',   name: 'Total Market ETF',   sector: 'ETF' },
];

const AV_BASE = 'https://www.alphavantage.co/query';
const LS_KEY  = 'stocktime_api_key';

let apiKey        = localStorage.getItem(LS_KEY) || '';
let selectedStock = null;
let priceChart    = null;
let searchTimer   = null;

const setupScreen  = document.getElementById('setup-screen');
const appEl        = document.getElementById('app');
const apiKeyInput  = document.getElementById('api-key-input');
const saveKeyBtn   = document.getElementById('save-api-key-btn');
const changeKeyBtn = document.getElementById('change-key-btn');
const searchInput  = document.getElementById('stock-search');
const dropdown     = document.getElementById('search-dropdown');
const selPill      = document.getElementById('selected-pill');
const pillTicker   = document.getElementById('pill-ticker');
const pillName     = document.getElementById('pill-name');
const clearBtn     = document.getElementById('clear-stock');
const amountInput  = document.getElementById('amount');
const calcBtn      = document.getElementById('calculate-btn');
const loadingEl    = document.getElementById('loading');
const errorEl      = document.getElementById('error-card');
const errorMsg     = document.getElementById('error-msg');
const resultsEl    = document.getElementById('results-card');
const stocksGrid   = document.getElementById('stocks-grid');

function boot() {
  if (apiKey) { showApp(); } else { showSetup(); }
  renderStocksGrid();
  bindEvents();
}

function showSetup() {
  setupScreen.classList.remove('hidden');
  appEl.classList.add('hidden');
}

function showApp() {
  appEl.classList.remove('hidden');
  setupScreen.classList.add('hidden');
}

function bindEvents() {
  saveKeyBtn.addEventListener('click', () => {
    const k = apiKeyInput.value.trim();
    if (!k) return;
    apiKey = k;
    localStorage.setItem(LS_KEY, k);
    showApp();
  });

  apiKeyInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') saveKeyBtn.click();
  });

  changeKeyBtn.addEventListener('click', () => {
    apiKeyInput.value = apiKey;
    showSetup();
  });

  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = searchInput.value.trim();
    if (!q) { closeDropdown(); return; }
    searchTimer = setTimeout(() => doSearch(q), 280);
  });

  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDropdown();
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('.search-wrapper')) closeDropdown();
  });

  clearBtn.addEventListener('click', clearStock);
  calcBtn.addEventListener('click', calculate);
}

async function doSearch(q) {
  const local = STOCKS.filter(s =>
    s.symbol.toLowerCase().includes(q.toLowerCase()) ||
    s.name.toLowerCase().includes(q.toLowerCase())
  ).slice(0, 8);

  if (local.length) {
    renderDropdown(local.map(s => ({ symbol: s.symbol, name: s.name, exchange: '' })));
    return;
  }

  try {
    const url = `${AV_BASE}?function=SYMBOL_SEARCH&keywords=${encodeURIComponent(q)}&apikey=${apiKey}`;
    const res  = await fetch(url);
    const data = await res.json();
    const hits = (data.bestMatches || [])
      .filter(m => m['4. region'] === 'United States')
      .slice(0, 8)
      .map(m => ({ symbol: m['1. symbol'], name: m['2. name'], exchange: m['3. type'] }));
    renderDropdown(hits);
  } catch {
    closeDropdown();
  }
}

function renderDropdown(items) {
  if (!items.length) { closeDropdown(); return; }
  dropdown.innerHTML = items.map(i => `
    <div class="dd-item" data-symbol="${i.symbol}" data-name="${escHtml(i.name)}">
      <span class="dd-symbol">${escHtml(i.symbol)}</span>
      <span class="dd-name">${escHtml(i.name)}</span>
      <span class="dd-exch">${escHtml(i.exchange || '')}</span>
    </div>
  `).join('');
  dropdown.querySelectorAll('.dd-item').forEach(el => {
    el.addEventListener('click', () => pickStock(el.dataset.symbol, el.dataset.name));
  });
  dropdown.classList.remove('hidden');
}

function closeDropdown() { dropdown.classList.add('hidden'); }

function pickStock(symbol, name) {
  selectedStock = { symbol, name };
  pillTicker.textContent = symbol;
  pillName.textContent   = name;
  searchInput.classList.add('gone');
  selPill.classList.remove('hidden');
  closeDropdown();
  calcBtn.disabled = false;
  calcBtn.textContent = `Calculate — ${symbol}`;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function clearStock() {
  selectedStock = null;
  searchInput.classList.remove('gone');
  searchInput.value = '';
  selPill.classList.add('hidden');
  calcBtn.disabled = true;
  calcBtn.textContent = 'Calculate';
  hideAll();
}

function renderStocksGrid() {
  stocksGrid.innerHTML = STOCKS.map(s => `
    <div class="stock-card" data-symbol="${s.symbol}" data-name="${escHtml(s.name)}">
      <div class="sc-sym">${s.symbol}</div>
      <div class="sc-name">${escHtml(s.name)}</div>
      <div class="sc-sect">${s.sector}</div>
    </div>
  `).join('');
  stocksGrid.querySelectorAll('.stock-card').forEach(el => {
    el.addEventListener('click', () => pickStock(el.dataset.symbol, el.dataset.name));
  });
}

async function calculate() {
  if (!selectedStock) return;

  const amount = parseFloat(amountInput.value);
  if (!amount || amount <= 0) { showError('Enter a valid dollar amount.'); return; }

  showLoading();

  try {
    const url = `${AV_BASE}?function=TIME_SERIES_DAILY` +
      `&symbol=${encodeURIComponent(selectedStock.symbol)}` +
      `&outputsize=full&apikey=${apiKey}`;

    const res  = await fetch(url);
    const data = await res.json();

    if (data['Note']) {
      showError('API rate limit reached (25 requests/day on free tier). Wait a minute and try again.');
      return;
    }
    if (data['Error Message'] || data['Information']) {
      showError(data['Error Message'] || data['Information'] || 'Symbol not found.');
      return;
    }

    const series = data['Time Series (Daily)'];
    if (!series) { showError('No data returned. Check the symbol and try again.'); return; }

    const prices = Object.entries(series)
      .map(([date, v]) => ({ date, close: parseFloat(v['4. close']) }))
      .filter(p => !isNaN(p.close))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (prices.length < 2) { showError('Not enough price data.'); return; }

    const today = new Date();
    const oneYearAgo = new Date(today);
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    const targetStr = fmtDate(oneYearAgo);

    const startIdx = prices.findIndex(p => p.date >= targetStr);
    if (startIdx === -1) { showError('Not enough historical data for a 1-year range.'); return; }

    const startPoint = prices[startIdx];
    const endPoint   = prices[prices.length - 1];
    const window     = prices.slice(startIdx);

    const meta        = data['Meta Data'] || {};
    const symbolLabel = meta['2. Symbol'] || selectedStock.symbol;

    displayResults({
      symbol:     symbolLabel,
      name:       selectedStock.name,
      exchange:   '',
      startDate:  startPoint.date,
      endDate:    endPoint.date,
      startPrice: startPoint.close,
      endPrice:   endPoint.close,
      prices:     window,
    }, amount);

  } catch (err) {
    showError('Network error. Check your connection and try again.');
    console.error(err);
  }
}

function displayResults(d, amount) {
  hideLoading();
  hideError();

  const shares   = amount / d.startPrice;
  const endValue = shares * d.endPrice;
  const gain     = endValue - amount;
  const pct      = ((d.endPrice - d.startPrice) / d.startPrice) * 100;
  const isPos    = gain >= 0;

  document.getElementById('res-ticker').textContent   = d.symbol;
  document.getElementById('res-name').textContent     = d.name;
  document.getElementById('res-exchange').textContent = d.exchange || 'NYSE / NASDAQ';

  const badge = document.getElementById('res-badge');
  badge.textContent = `${isPos ? '+' : ''}${pct.toFixed(2)}%`;
  badge.className   = `return-badge ${isPos ? 'pos' : 'neg'}`;

  document.getElementById('res-invested').textContent   = fmt(amount);
  document.getElementById('res-date-start').textContent = fmtDateDisp(d.startDate);
  document.getElementById('res-value').textContent      = fmt(endValue);
  document.getElementById('res-date-end').textContent   = fmtDateDisp(d.endDate);

  document.getElementById('d-price-start').textContent = fmt(d.startPrice);
  document.getElementById('d-price-end').textContent   = fmt(d.endPrice);
  document.getElementById('d-shares').textContent      = shares.toFixed(6);

  const gainEl = document.getElementById('d-gain');
  gainEl.textContent = `${isPos ? '+' : ''}${fmt(gain)} (${isPos ? '+' : ''}${pct.toFixed(2)}%)`;
  gainEl.className   = `dv ${isPos ? 'pos' : 'neg'}`;

  drawChart(d.prices, d.symbol, isPos);
  resultsEl.classList.remove('hidden');
}

function drawChart(prices, symbol, isPos) {
  const ctx = document.getElementById('price-chart').getContext('2d');
  if (priceChart) { priceChart.destroy(); priceChart = null; }

  const color = isPos ? '#22c55e' : '#ef4444';
  const fill  = isPos ? 'rgba(34,197,94,.1)' : 'rgba(239,68,68,.1)';

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: prices.map(p => p.date),
      datasets: [{
        label: symbol,
        data:  prices.map(p => p.close),
        borderColor: color,
        backgroundColor: fill,
        borderWidth: 2,
        fill: true,
        tension: 0.25,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#192033',
          borderColor: '#1d2d44',
          borderWidth: 1,
          titleColor: '#8892a4',
          bodyColor: '#e2e8f0',
          callbacks: { label: ctx => ` $${ctx.parsed.y.toFixed(2)}` }
        }
      },
      scales: {
        x: {
          grid: { color: '#1d2d44' },
          ticks: { color: '#3d4f66', maxTicksLimit: 7, font: { size: 11 }, maxRotation: 0 }
        },
        y: {
          grid: { color: '#1d2d44' },
          ticks: { color: '#3d4f66', font: { size: 11 }, callback: v => '$' + v.toLocaleString() }
        }
      }
    }
  });
}

function showLoading() {
  loadingEl.classList.remove('hidden');
  errorEl.classList.add('hidden');
  resultsEl.classList.add('hidden');
}
function hideLoading() { loadingEl.classList.add('hidden'); }
function showError(msg) {
  hideLoading();
  resultsEl.classList.add('hidden');
  errorMsg.textContent = msg;
  errorEl.classList.remove('hidden');
}
function hideError() { errorEl.classList.add('hidden'); }
function hideAll() {
  loadingEl.classList.add('hidden');
  errorEl.classList.add('hidden');
  resultsEl.classList.add('hidden');
}

function fmt(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 2, maximumFractionDigits: 2
  }).format(n);
}

function fmtDate(d) {
  return d.toISOString().split('T')[0];
}

function fmtDateDisp(s) {
  return new Date(s + 'T12:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  });
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

boot();