<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';

const chartContainer = ref(null);
const status = ref('Connecting');
const source = ref('Yahoo Finance');
const receivedAt = ref('—');
const latestBar = ref('—');
const age = ref('—');
const count = ref(0);
const message = ref('');
const mode = ref('Connecting to Yahoo Finance…');
const backtest = ref(null);
const backtestError = ref('');
const shortWindow = ref(10);
const longWindow = ref(30);
const apiBase = 'http://127.0.0.1:8001';
let shortSeries, longSeries;
let chart, candleSeries, volumeSeries, socket, timer, resizeObserver;

async function runSimulation() {
  try {
    const response = await fetch(`${apiBase}/api/backtest?short=${shortWindow.value}&long=${longWindow.value}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Backtest failed');
    backtest.value = data;
    backtestError.value = '';
    const toPoints = (key) => data.indicators.filter(r => r[key] !== null).map(r => ({time:Math.floor(new Date(r.time).getTime()/1000),value:r[key]}));
    shortSeries?.setData(toPoints('short_sma'));
    longSeries?.setData(toPoints('long_sma'));
  } catch (error) { backtestError.value = error.message; }
}

function showCandles(rows) {
  if (!candleSeries || !volumeSeries) return;
  const valid = rows.map(r => ({...r, timestamp: Math.floor(new Date(r.candle_time ?? r.time).getTime() / 1000)}))
    .filter(r => Number.isFinite(r.timestamp) && Number.isFinite(Number(r.close)))
    .sort((a, b) => a.timestamp - b.timestamp);
  const deduped = [...new Map(valid.map(r => [r.timestamp, r])).values()];
  candleSeries.setData(deduped.map(r => ({time:r.timestamp,open:+r.open,high:+r.high,low:+r.low,close:+r.close})));
  volumeSeries.setData(deduped.map(r => ({time:r.timestamp,value:+r.volume,color:+r.close >= +r.open ? '#22c55e88' : '#ef444488'})));
  count.value = deduped.length;
  latestBar.value = deduped.length ? new Date(deduped.at(-1).timestamp * 1000).toLocaleString() : '—';
  const lastTime = deduped.at(-1)?.timestamp;
  age.value = lastTime ? `${Math.max(0, Math.floor(Date.now()/1000-lastTime))} seconds` : '—';
  if (deduped.length) chart.timeScale().fitContent();
  runSimulation();
}

async function loadStored() {
  try {
    const response = await fetch(`${apiBase}/api/candles`);
    if (!response.ok) throw new Error('Unable to retrieve stored candles');
    const data = await response.json();
    showCandles(data.candles);
    mode.value = 'Stored observations loaded (replay view)';
  } catch (error) { message.value = error.message; }
}

function connect() {
  socket = new WebSocket('ws://127.0.0.1:8001/ws/market');
  socket.onopen = () => { status.value = 'Connected to backend'; message.value = ''; };
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    status.value = data.status;
    source.value = data.source ?? 'Yahoo Finance';
    receivedAt.value = data.received_at ? new Date(data.received_at).toLocaleString() : '—';
    message.value = data.message ?? '';
    showCandles(data.candles ?? []);
    mode.value = data.status === 'receiving' ? 'Yahoo Finance polling (not a verified tick stream)' : 'Stored-data fallback';
  };
  socket.onerror = () => { status.value = 'WebSocket error'; };
  socket.onclose = () => { status.value = 'Disconnected'; mode.value = 'Stored-data fallback'; };
}

onMounted(() => {
  chart = createChart(chartContainer.value, {
    autoSize:true, layout:{background:{color:'#0b1023'},textColor:'#aab8df'},
    grid:{vertLines:{color:'#202a4c'},horzLines:{color:'#202a4c'}},
    timeScale:{timeVisible:true,secondsVisible:false}
  });
  candleSeries = chart.addSeries(CandlestickSeries, {upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444',priceScaleId:'right'});
  shortSeries = chart.addSeries(LineSeries, {color:'#a78bfa',lineWidth:2,priceScaleId:'right',title:'Short SMA'});
  longSeries = chart.addSeries(LineSeries, {color:'#44d5ff',lineWidth:2,priceScaleId:'right',title:'Long SMA'});
  volumeSeries = chart.addSeries(HistogramSeries, {priceFormat:{type:'volume'},priceScaleId:'volume'});
  chart.priceScale('right').applyOptions({scaleMargins:{top:0.08,bottom:0.27}});
  chart.priceScale('volume').applyOptions({scaleMargins:{top:0.78,bottom:0}});
  loadStored().then(connect);
  timer = setInterval(() => {
    if (latestBar.value !== '—') {
      const match = latestBar.value;
      // Age is refreshed from the latest stored candle timestamp on each data update.
    }
  }, 1000);
});
onUnmounted(() => {socket?.close(); clearInterval(timer); chart?.remove(); resizeObserver?.disconnect();});
</script>

<template>
  <main>
    <nav class="topbar"><div class="brand-mark">✦</div><div class="brand-name">NOVA<span>TERMINAL</span></div><div class="nav-divider"></div><span class="nav-caption">MARKET INTELLIGENCE / WORKSTATION</span><div class="nav-spacer"></div><span class="market-chip"><span class="live-dot"></span> AAPL · NASDAQ</span><span class="nav-version">v 4.2</span></nav>
    <header><div><p class="eyebrow">/ STRATEGY OPERATIONS CENTER &nbsp;·&nbsp; ASSIGNMENT 4.2</p><h1>Trade smarter<span class="headline-period">.</span><br/><span class="gradient-title">See further.</span></h1><p>Apple Inc. <span class="header-separator">/</span> NASDAQ: AAPL <span class="header-separator">/</span> 1-minute market observations</p></div><span class="pill">{{ status }}</span></header>
    <div class="section-label"><span>01</span> MARKET TELEMETRY <div class="section-rule"></div> <span class="section-meta">LIVE WORKSPACE</span></div>
    <section class="metrics">
      <div><label>DATA SOURCE</label><strong>{{ source }}</strong></div>
      <div><label>FEED MODE</label><strong>{{ mode }}</strong></div>
      <div><label>LAST RECEIVED</label><strong>{{ receivedAt }}</strong></div>
      <div><label>NEWEST BAR / AGE</label><strong>{{ latestBar }} · {{ age }}</strong></div>
      <div><label>STORED CANDLES</label><strong>{{ count }}</strong></div>
    </section>
    <div class="section-label"><span>02</span> PRICE ACTION <div class="section-rule"></div><span class="section-meta">OHLCV / SMA OVERLAY</span></div>
    <section class="panel chart-panel"><div class="panel-title"><div><span class="mini-label">CHART / 01</span><h2>AAPL <span class="muted-heading">/ Candlesticks & Volume</span></h2></div><button @click="loadStored">↻ &nbsp; Load stored data</button></div><div ref="chartContainer" class="chart"></div></section>
    <div class="section-label"><span>03</span> STRATEGY ENGINE <div class="section-rule"></div><span class="section-meta">SIMULATION / BACKTEST</span></div>
    <section class="panel simulation">
      <div class="panel-title"><div><span class="mini-label">STRATEGY / 01</span><h2>SMA crossover <span class="muted-heading">/ Backtesting Lab</span></h2></div><button @click="runSimulation">▶ &nbsp; Run backtest</button></div>
      <div class="settings"><label>Short SMA <input type="number" min="1" v-model.number="shortWindow" /></label><label>Long SMA <input type="number" min="2" v-model.number="longWindow" /></label></div>
      <p class="notice" v-if="backtestError">{{ backtestError }}</p>
      <template v-if="backtest">
        <p>{{ backtest.assumptions }}</p>
        <p>Completed candles analyzed: {{ backtest.bars_used }} · Crossovers: {{ backtest.indicators.filter(i => i.signal !== 'HOLD').length }}</p>
        <div class="metrics account">
          <div><label>CASH</label><strong>${{ backtest.account.cash.toLocaleString() }}</strong></div>
          <div><label>POSITION</label><strong>{{ backtest.account.shares }} AAPL</strong></div>
          <div><label>REALIZED P/L</label><strong>${{ backtest.account.realized_pnl.toLocaleString() }}</strong></div>
          <div><label>UNREALIZED P/L</label><strong>${{ backtest.account.unrealized_pnl.toLocaleString() }}</strong></div>
          <div><label>EQUITY / RETURN</label><strong>${{ backtest.account.total_equity.toLocaleString() }} / {{ backtest.account.total_return_pct }}%</strong></div>
          <div><label>MAX DRAWDOWN</label><strong>{{ backtest.account.max_drawdown_pct }}%</strong></div>
        </div>
        <h3><span class="subsection-index">01 /</span> Trade history <small>Next-bar open fills</small></h3>
        <div class="table-scroll"><table><thead><tr><th>Time</th><th>Side</th><th>Shares</th><th>Fill price</th><th>Fee</th><th>Realized P/L</th><th>Cash after</th></tr></thead>
          <tbody><tr v-for="(trade, i) in backtest.trades" :key="i"><td>{{ new Date(trade.time).toLocaleString() }}</td><td>{{ trade.side }}</td><td>{{ trade.quantity }}</td><td>${{ trade.price.toFixed(2) }}</td><td>${{ trade.fee.toFixed(2) }}</td><td>${{ trade.realized_pnl.toFixed(2) }}</td><td>${{ trade.cash_after.toFixed(2) }}</td></tr></tbody></table></div>
        <p v-if="!backtest.trades.length">No fills occurred for these parameters and completed candles.</p>
        <h3><span class="subsection-index">02 /</span> Equity over time</h3>
        <div class="table-scroll"><table><thead><tr><th>Timestamp</th><th>Equity</th></tr></thead><tbody><tr v-for="(point, i) in backtest.equity_curve.filter((_,i) => i % Math.max(1,Math.ceil(backtest.equity_curve.length/15)) === 0 || i === backtest.equity_curve.length-1)" :key="i"><td>{{ new Date(point.time).toLocaleString() }}</td><td>${{ point.equity.toLocaleString() }}</td></tr></tbody></table></div>
      </template>
    </section>
    <p class="notice" v-if="message">Feed notice: {{ message }}</p>
    <p class="footer">Educational dashboard · Not investment advice · Yahoo Finance intraday data may be delayed or unavailable. A WebSocket from the backend does not prove a live Yahoo tick stream.</p>
  </main>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{font-family:'DM Sans',system-ui,sans-serif;color:#eaf0ff;background:#080d1c;font-synthesis:none}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse 70% 25% at 80% 0%,#28215c77,transparent 75%),radial-gradient(ellipse 45% 24% at 0% 36%,#0d315277,transparent 80%),#080d1c;color:#eaf0ff}main{max-width:1510px;margin:auto;padding:0 40px 45px}.topbar{display:flex;align-items:center;gap:15px;height:82px;border-bottom:1px solid #ffffff14;margin-bottom:49px}.brand-mark{display:grid;place-items:center;background:linear-gradient(135deg,#715bff,#35c8ff);border-radius:12px;width:38px;height:38px;font-size:23px;box-shadow:0 0 28px #7760ff66}.brand-name{font:700 18px 'Space Grotesk',sans-serif;letter-spacing:1.1px}.brand-name span{color:#9588ff}.nav-divider{height:23px;width:1px;background:#ffffff2b;margin:0 8px}.nav-caption,.nav-version{font-size:10px;color:#8292ba;letter-spacing:1.6px}.nav-spacer{flex:1}.market-chip{border:1px solid #3c4773;background:#151e3c;border-radius:20px;padding:10px 14px;font-size:11px;font-weight:700;letter-spacing:.7px}.live-dot{display:inline-block;width:7px;height:7px;background:#26e2c2;border-radius:50%;box-shadow:0 0 12px #26e2c2;margin-right:7px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:42px}h1,h2,h3{font-family:'Space Grotesk',sans-serif}h1{font-size:clamp(37px,4.3vw,64px);line-height:1.08;letter-spacing:-2.6px;margin:16px 0 18px;font-weight:700}.headline-period{color:#8c7cff}.gradient-title{background:linear-gradient(100deg,#a38aff,#51c7ff);color:transparent;background-clip:text}header p{color:#96a5c7;font-size:13px;margin:0}.header-separator{color:#566588;margin:0 8px}.eyebrow{font-size:11px;letter-spacing:2.4px;color:#8f84ff;font-weight:700}.pill{padding:11px 16px;border:1px solid #3a4771;border-radius:25px;background:#151e3b;color:#a8f8e8;font-size:12px;text-transform:uppercase;letter-spacing:1px;font-weight:700}.section-label{display:flex;align-items:center;gap:13px;color:#c3cae6;font-size:10px;letter-spacing:2px;font-weight:700;margin:26px 0 15px}.section-label>span:first-child{color:#9b87ff}.section-rule{height:1px;background:#2b3455;flex:1}.section-meta{color:#68769b}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px;margin-bottom:29px}.metrics>div,.panel{background:linear-gradient(145deg,#141d37,#10172d);border:1px solid #2b3659;border-radius:16px;box-shadow:0 12px 34px #00000025}.metrics>div{padding:21px 18px;min-width:0;position:relative;overflow:hidden}.metrics>div:before{content:'';position:absolute;top:0;left:18px;right:18px;height:2px;background:linear-gradient(90deg,#8c76ff,#3abcfb,transparent);opacity:.8}.metrics label{display:block;color:#8797bb;font-size:10px;letter-spacing:1.6px;margin-bottom:14px;font-weight:700}.metrics strong{font:600 13px 'Space Grotesk',sans-serif;overflow-wrap:anywhere;line-height:1.55}.panel{padding:23px 25px;margin-bottom:28px}.panel-title{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:20px}.panel h2{font-size:20px;letter-spacing:-.4px;margin:6px 0}.mini-label{color:#8c83b6;font-size:10px;letter-spacing:1.7px;font-weight:700}.muted-heading{color:#9aabd1;font-weight:400}.panel button{background:linear-gradient(110deg,#7760fa,#4d7ef8);color:white;border:1px solid #9b92ff66;border-radius:10px;padding:12px 17px;font-weight:700;font-size:12px;cursor:pointer;box-shadow:0 7px 25px #6658f82b}.panel button:hover{filter:brightness(1.16)}.chart{height:510px;width:100%;border:1px solid #293252;border-radius:9px;overflow:hidden}.simulation{margin-top:0}.settings{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0 22px}.settings label{color:#a7b5d7;font-size:12px;font-weight:600}.settings input{display:block;background:#0b1329;color:white;border:1px solid #44517a;padding:10px 12px;border-radius:9px;width:125px;margin-top:8px;font:600 14px 'Space Grotesk',sans-serif;outline:none}.settings input:focus{border-color:#9b88ff;box-shadow:0 0 0 3px #8c76ff22}.account{grid-template-columns:repeat(3,minmax(0,1fr));margin:20px 0 32px}.simulation h3{font-size:17px;margin:28px 0 14px}.simulation h3 small{font:400 12px 'DM Sans',sans-serif;color:#8d9ec1;margin-left:8px}.subsection-index{color:#9884ff;font-size:12px}.table-scroll{overflow:auto;border:1px solid #2d395d;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:13px 14px;border-bottom:1px solid #293554;text-align:left;white-space:nowrap}th{background:#1a2545;color:#aab8df;letter-spacing:.6px;font-size:10px}td{color:#d3def6}tbody tr:hover{background:#1b2644}.simulation p{color:#a8b8d8;line-height:1.7;font-size:13px}.notice{color:#ffcc7c}.footer{font-size:11px;color:#7788ac;margin-top:30px;border-top:1px solid #273251;padding-top:22px;line-height:1.6}@media(max-width:1050px){.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.account{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:650px){main{padding:0 16px 25px}.topbar{height:68px;margin-bottom:30px}.nav-caption,.nav-divider,.nav-version{display:none}header{flex-direction:column;margin-bottom:30px}h1{letter-spacing:-1.4px}.metrics,.account{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{padding:16px}.panel-title{align-items:flex-start;flex-direction:column}.chart{height:390px}.section-meta{display:none}}
</style>
