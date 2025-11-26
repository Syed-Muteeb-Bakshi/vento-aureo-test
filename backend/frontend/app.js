/* app.js - Vento Aureo demo frontend
   Replace CLOUD_BASE with your Cloud Run base URL if different.
*/

const CLOUD_BASE = "https://vento-backend-678919375946.us-east1.run.app";
const DEVICES = [
  { id: "PORTABLE-01", name: "Portable (PORTABLE-01)" },
  { id: "Vento-Station-01", name: "Static Station (Vento-Station-01)" }
];

const REFRESH_MS = 5000;
let currentDevice = DEVICES[0].id;
let autoTimer = null;

/* DOM */
const deviceSelector = document.getElementById("deviceSelector");
const statusEl = document.getElementById("status");
const cardsEl = document.getElementById("cards");
const jsonDump = document.getElementById("jsonDump");
const lastSeen = document.getElementById("lastSeen");
const mapFallback = document.getElementById("mapFallback");

/* charts */
let tempChart = null, pmChart = null, gasChart = null;

/* map */
let map = null, marker = null;

function init() {
  // fill selector
  DEVICES.forEach(d => {
    const opt = document.createElement("option");
    opt.value = d.id; opt.textContent = d.name;
    deviceSelector.appendChild(opt);
  });
  deviceSelector.value = currentDevice;
  deviceSelector.onchange = () => {
    currentDevice = deviceSelector.value;
    resetData();
    fetchAndRender();
  };

  document.getElementById("refreshBtn").onclick = () => fetchAndRender();

  // cards placeholders
  renderCards({});

  // charts
  const tctx = document.getElementById("tempChart").getContext("2d");
  tempChart = new Chart(tctx, {
    type: "line",
    data: { labels: [], datasets: [{ label: "Temp °C", data: [], tension:0.3, fill:false }] },
    options: { responsive:true, plugins:{legend:{display:false}} }
  });

  const pmctx = document.getElementById("pmChart").getContext("2d");
  pmChart = new Chart(pmctx, {
    type: "line",
    data: { labels: [], datasets: [
      { label: "PM2.5", data: [], tension:0.3, fill:false },
      { label: "PM10", data: [], tension:0.3, fill:false }
    ]},
    options: { responsive:true }
  });

  const gctx = document.getElementById("gasChart").getContext("2d");
  gasChart = new Chart(gctx, {
    type: "line",
    data: { labels: [], datasets: [
      { label: "VOC/Raw", data: [], tension:0.3, fill:false },
      { label: "CO₂ (ppm)", data: [], tension:0.3, fill:false }
    ]},
    options: { responsive:true }
  });

  // map
  map = L.map('map', { zoomControl:false }).setView([20.59,78.96], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);

  fetchAndRender();
  autoTimer = setInterval(fetchAndRender, REFRESH_MS);
}

function resetData(){
  // clear chart data
  [tempChart, pmChart, gasChart].forEach(ch => {
    ch.data.labels = []; ch.data.datasets.forEach(ds => ds.data = []);
    ch.update();
  });
  if (marker) { map.removeLayer(marker); marker = null; }
  jsonDump.textContent = "";
  lastSeen.textContent = "—";
  mapFallback.textContent = "";
}

async function fetchAndRender(){
  statusEl.textContent = "Loading...";
  try {
    const url = `${CLOUD_BASE}/api/visual_report?device_id=${encodeURIComponent(currentDevice)}`;
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    statusEl.textContent = "OK";
    renderFromAPI(j);
  } catch (e){
    statusEl.textContent = "Error: " + e.message;
    console.error(e);
  }
}

function renderFromAPI(data){
  // data.latest is assumed; adapt if structure differs
  const latest = data.latest || data;
  jsonDump.textContent = JSON.stringify(latest, null, 2);

  // cards right-top
  renderCards(latest);

  // time
  lastSeen.textContent = latest.timestamp || latest.received_at || "no timestamp";

  // charts - keep rolling window of 20
  addPoint(tempChart, latest.timestamp || new Date().toISOString(), latest.temperature);
  addPoint(pmChart, latest.timestamp || new Date().toISOString(), latest.pm25, 0);
  addPoint(pmChart, latest.timestamp || new Date().toISOString(), latest.pm10, 1);
  addPoint(gasChart, latest.timestamp || new Date().toISOString(), latest.voc_ppm || latest.bme_gas || latest.mq135, 0);
  addPoint(gasChart, latest.timestamp || new Date().toISOString(), latest.co2, 1);

  // map
  const gps = latest.gps || (latest.latitude && latest.longitude ? { lat: latest.latitude, lon: latest.longitude } : null);
  if (gps && gps.lat && gps.lon) {
    mapFallback.textContent = "";
    const lat = parseFloat(gps.lat), lon = parseFloat(gps.lon);
    if (!marker) marker = L.marker([lat, lon]).addTo(map);
    else marker.setLatLng([lat, lon]);
    map.setView([lat, lon], 14);
  } else {
    mapFallback.textContent = "GPS: unavailable";
  }
}

function renderCards(latest){
  const cardHtml = (k, v, u="") => `
    <div class="card">
      <div class="text-slate-400 text-sm">${k}</div>
      <div class="mt-2 text-2xl font-semibold">${v===undefined || v===null ? "—" : v} ${u}</div>
    </div>`;
  cardsEl.innerHTML = `
    ${cardHtml("Temperature", latest.temperature, "°C")}
    ${cardHtml("Humidity", latest.humidity, "%")}
    ${cardHtml("Pressure", latest.pressure, "hPa")}
    ${cardHtml("PM2.5", latest.pm25)}
    ${cardHtml("PM10", latest.pm10)}
    ${cardHtml("CO₂", latest.co2, "ppm")}
    ${cardHtml("VOC", latest.voc_ppm)}
    ${cardHtml("MQ raw", latest.mq135)}
  `;
}

function addPoint(chart, label, value, datasetIdx=0){
  if (!chart) return;
  // if dataset array length mismatch, ensure dataset exists
  while (chart.data.datasets.length <= datasetIdx) chart.data.datasets.push({data:[]});
  chart.data.labels.push(label ? new Date(label).toLocaleTimeString() : new Date().toLocaleTimeString());
  chart.data.datasets[datasetIdx].data.push((value===undefined || value===null) ? null : Number(value));
  // keep last 20
  if (chart.data.labels.length > 20) {
    chart.data.labels.shift();
    chart.data.datasets.forEach(ds => ds.data.shift());
  }
  chart.update();
}

// init on load
window.addEventListener('load', init);
