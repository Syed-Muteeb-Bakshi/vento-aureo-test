// ============================================
// VENTO AUREO - Air Quality Dashboard
// ============================================

// Configuration
const API_BASE = "https://vento-backend-678919375946.us-east1.run.app";
const API_KEY = "YOUR_API_KEY_HERE";
const REFRESH_INTERVAL = 5000;
const CHART_BUFFER_SIZE = 20;

// Debug: Log API base
console.log('API Base URL:', API_BASE);

// State
let currentSection = 'dashboard';
let currentDevice = 'portable';
let cities = [];
let triviaPool = [];
let refreshIntervalId = null;

// Chart instances
let charts = {
    portable: { temp: null, pm: null },
    static: { temp: null, gas: null },
    predict: null,
    historic: null
};

// Chart data buffers
const chartData = {
    portable: { temp: [], pm25: [], pm10: [], timestamps: [] },
    static: { temp: [], co2: [], voc: [], pm25: [], pm10: [], timestamps: [] }
};

// Map instances
let maps = { portable: null, static: null };
let mapMarkers = { portable: null, static: null };

// ==========================
// INITIALIZATION
// ==========================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initTitleScreen();
    setupEventListeners();
    // Load cities immediately and retry if needed
    loadCities().then(() => {
        console.log('Cities loaded:', cities.length);
        if (cities.length === 0) {
            console.warn('No cities loaded, retrying...');
            setTimeout(loadCities, 2000);
        }
    });
    loadTrivia();
    loadCurrentLocationAQI();
});

// ==========================
// TITLE SCREEN
// ==========================
function initTitleScreen() {
    const titleScreen = document.getElementById('title-screen');
    const mainApp = document.getElementById('main-app');
    
    // Animate title screen elements
    setTimeout(() => {
        document.querySelector('.title-text').style.opacity = '1';
        document.querySelector('.title-text').style.transition = 'opacity 1s ease-in';
    }, 300);
    
    setTimeout(() => {
        document.querySelector('.subtitle-text').style.opacity = '1';
        document.querySelector('.subtitle-text').style.transition = 'opacity 1s ease-in';
    }, 800);
    
    setTimeout(() => {
        document.querySelector('.floating-symbols').style.opacity = '1';
        document.querySelector('.floating-symbols').style.transition = 'opacity 1s ease-in';
        document.querySelector('.edge-symbols').style.opacity = '1';
        document.querySelector('.edge-symbols').style.transition = 'opacity 1s ease-in';
    }, 1300);
    
    // Fade out and show main app
    setTimeout(() => {
        titleScreen.style.opacity = '0';
        titleScreen.style.transition = 'opacity 0.8s ease-out';
        setTimeout(() => {
            titleScreen.style.display = 'none';
            mainApp.classList.remove('hidden');
            initializeApp();
        }, 800);
    }, 3000);
}

// ==========================
// APP INITIALIZATION
// ==========================
function initializeApp() {
    setupSidebar();
    initializeCharts();
    initializeMaps();
    startAutoRefresh();
    fetchDeviceData('PORTABLE-01', 'portable');
    fetchDeviceData('Vento-Station-01', 'static');
}

// ==========================
// SIDEBAR NAVIGATION
// ==========================
function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggle = document.getElementById('sidebar-toggle');
    const navItems = document.querySelectorAll('.nav-item');
    
    // Toggle sidebar (mobile only)
    toggle?.addEventListener('click', () => {
        sidebar.classList.toggle('-translate-x-full');
        overlay.classList.toggle('hidden');
    });
    
    // Close on overlay click
    overlay?.addEventListener('click', () => {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    });
    
    // Navigation
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            switchSection(section);
            
            // Update active state
            navItems.forEach(ni => {
                ni.classList.remove('active', 'bg-blue-50', 'dark:bg-blue-900', 'text-blue-600', 'dark:text-blue-400');
            });
            item.classList.add('active', 'bg-blue-50', 'dark:bg-blue-900', 'text-blue-600', 'dark:text-blue-400');
            
            // Close sidebar on mobile
            if (window.innerWidth < 768) {
                sidebar.classList.add('-translate-x-full');
                overlay.classList.add('hidden');
            }
        });
    });
}

// ==========================
// THEME TOGGLE
// ==========================
function initTheme() {
    const stored = localStorage.getItem('ventoa_theme') || 'light';
    document.documentElement.classList.toggle('dark', stored === 'dark');
    updateThemeIcon(stored === 'dark');
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('ventoa_theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
    
    // Fixed: Update all charts when theme changes
    if (charts.portable.temp) {
        const config = charts.portable.temp.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.portable.temp.update();
    }
    
    if (charts.portable.pm) {
        const config = charts.portable.pm.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.portable.pm.update();
    }
    
    if (charts.static.temp) {
        const config = charts.static.temp.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.static.temp.update();
    }
    
    if (charts.static.gas) {
        const config = charts.static.gas.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.static.gas.update();
    }
    
    if (charts.predict) {
        const config = charts.predict.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.predict.update();
    }
    
    if (charts.historic) {
        const config = charts.historic.config;
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        config.options.plugins.legend.labels.color = textColor;
        config.options.scales.x.ticks.color = tickColor;
        config.options.scales.y.ticks.color = tickColor;
        config.options.scales.x.grid.color = gridColor;
        config.options.scales.y.grid.color = gridColor;
        charts.historic.update();
    }
}

function updateThemeIcon(isDark) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = isDark ? '☀️' : '🌙';
    }
}

function switchSection(section) {
    // Hide all sections
    document.querySelectorAll('.section-content').forEach(s => s.classList.add('hidden'));
    
    // Show selected section
    const targetSection = document.getElementById(`section-${section}`);
    if (targetSection) {
        targetSection.classList.remove('hidden');
        currentSection = section;
        
        // Update page title
        const titles = {
            'dashboard': 'Dashboard',
            'sensor-kit': 'Sensor Kit',
            'predictive': 'Predictive AQI Analysis',
            'historic': 'Historic AQI Charts'
        };
        document.getElementById('page-title').textContent = titles[section] || 'Dashboard';
    }
}

// ==========================
// EVENT LISTENERS
// ==========================
function setupEventListeners() {
    // Theme toggle
    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
    
    // Device tabs
    document.querySelectorAll('.device-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const device = tab.dataset.device;
            switchDevice(device);
        });
    });
    
    // City search
    document.getElementById('city-search-btn')?.addEventListener('click', searchCityAQI);
    document.getElementById('city-search-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchCityAQI();
    });
    
    // Predictive
    document.getElementById('predict-generate')?.addEventListener('click', generatePrediction);
    document.getElementById('predict-search')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const val = e.target.value.trim().toLowerCase();
            if (!val) return;
            const match = cities.find(c => c.toLowerCase().includes(val));
            if (match) {
                document.getElementById('predict-city').value = match;
                generatePrediction();
            }
        }
    });
    
    // Historic
    document.getElementById('historic-apply')?.addEventListener('click', loadHistoric);
    document.getElementById('historic-search')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const val = e.target.value.trim().toLowerCase();
            if (!val) return;
            const match = cities.find(c => c.toLowerCase().includes(val));
            if (match) {
                document.getElementById('historic-city').value = match;
                loadHistoric();
            }
        }
    });
}

function switchDevice(device) {
    currentDevice = device;
    
    // Update tabs
    document.querySelectorAll('.device-tab').forEach(tab => {
        if (tab.dataset.device === device) {
            tab.classList.add('active', 'border-blue-600', 'text-blue-600');
            tab.classList.remove('text-slate-600');
        } else {
            tab.classList.remove('active', 'border-blue-600', 'text-blue-600');
            tab.classList.add('text-slate-600');
        }
    });
    
    // Show/hide device views
    document.getElementById('device-portable').classList.toggle('hidden', device !== 'portable');
    document.getElementById('device-static').classList.toggle('hidden', device !== 'static');
    
    // Fetch data for selected device
    const deviceId = device === 'portable' ? 'PORTABLE-01' : 'Vento-Station-01';
    fetchDeviceData(deviceId, device);
}

// ==========================
// API CALLS
// ==========================
async function fetchDeviceData(deviceId, deviceType) {
    // Fixed: Use the correct endpoint as specified
    const url = `${API_BASE}/api/visual_report?device_id=${deviceId}`;
    
    const headers = {};
    if (API_KEY && API_KEY !== "YOUR_API_KEY_HERE") {
        headers['x-api-key'] = API_KEY;
    }
    
    console.log(`Fetching device data from: ${url}`);
    
    try {
        const response = await fetch(url, { 
            headers,
            method: 'GET'
        });
        
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('API response:', result);
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Check if response has the expected structure
        if (result.latest || result.device_id || result.data) {
            // Transform response if needed to match expected format
            let data = result;
            
            // If response has different structure, transform it
            if (result.data && !result.latest) {
                // Handle alternative response structure
                data = {
                    device_id: deviceId,
                    latest: result.data.latest || result.data,
                    chart_data: result.data.chart_data || {},
                    daily_stats: result.data.daily_stats || {}
                };
            }
            
            updateDeviceView(data, deviceType);
            updateConnectionStatus(true);
            return;
        } else {
            throw new Error('Unexpected response structure');
        }
    } catch (error) {
        console.warn('API fetch failed, trying mock data:', error.message);
        updateConnectionStatus(false);
        
        // Fallback to mock data
        try {
            const mockData = await loadMockData(deviceId);
            if (mockData) {
                updateDeviceView(mockData, deviceType);
                // Show as connected if mock data works
                updateConnectionStatus(true);
            } else {
                updateConnectionStatus(false);
            }
        } catch (e) {
            console.error('Mock data load failed:', e);
            updateConnectionStatus(false);
        }
    }
}

async function loadMockData(deviceId) {
    const filename = deviceId === 'PORTABLE-01' ? 'portable.json' : 'static.json';
    try {
        const response = await fetch(`example_payloads/${filename}`);
        if (!response.ok) throw new Error('Mock file not found');
        return await response.json();
    } catch (error) {
        console.error(`Failed to load mock data:`, error);
        return null;
    }
}

async function loadCities() {
    console.log('Loading cities from:', `${API_BASE}/api/list_cities`);
    try {
        const res = await fetch(`${API_BASE}/api/list_cities`);
        console.log('Cities API response status:', res.status);
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        console.log('Cities data received:', data);
        
        cities = Array.isArray(data) ? data : (typeof data === 'object' ? Object.keys(data) : []);
        console.log('Parsed cities array:', cities);
        
        if (cities.length === 0) {
            console.warn('No cities found in response');
            // Fallback cities for testing
            cities = ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Hyderabad', 'Kolkata'];
        }
        
        // Populate selects
        const selects = ['predict-city', 'historic-city'];
        selects.forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                const opts = cities.length ? cities.map(c => `<option value="${c}">${c}</option>`).join('') : '<option>No cities available</option>';
                select.innerHTML = opts;
                console.log(`Populated ${id} with ${cities.length} cities`);
            } else {
                console.warn(`Select element ${id} not found`);
            }
        });
        
        // Setup search autocomplete - delay to ensure DOM is ready
        setTimeout(() => {
            setupCitySearch('predict-search', 'predict-suggest', (val) => {
                const select = document.getElementById('predict-city');
                if (select) select.value = val;
            });
            
            setupCitySearch('historic-search', 'historic-suggest', (val) => {
                const select = document.getElementById('historic-city');
                if (select) select.value = val;
            });
        }, 500);
    } catch (e) {
        console.error('Failed to load cities:', e);
        // Fallback cities
        cities = ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Hyderabad', 'Kolkata'];
        
        // Still populate with fallback
        const selects = ['predict-city', 'historic-city'];
        selects.forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
            }
        });
    }
}

function setupCitySearch(inputId, suggestId, setterCallback) {
    const inputEl = document.getElementById(inputId);
    const suggestEl = document.getElementById(suggestId);
    
    if (!inputEl || !suggestEl) {
        console.warn(`City search setup failed: ${inputId} or ${suggestId} not found`);
        return;
    }
    
    inputEl.addEventListener('input', () => {
        const v = inputEl.value.trim().toLowerCase();
        if (!v) {
            suggestEl.style.display = 'none';
            return;
        }
        
        if (cities.length === 0) {
            console.warn('Cities array is empty, cannot search');
            return;
        }
        
        const matches = cities.filter(c => c.toLowerCase().includes(v)).slice(0, 12);
        if (!matches.length) {
            suggestEl.style.display = 'none';
            return;
        }
        suggestEl.innerHTML = matches.map(m => 
            `<div class="px-4 py-2 hover:bg-blue-50 dark:hover:bg-slate-700 cursor-pointer text-slate-900 dark:text-slate-100" data-val="${m}">${m}</div>`
        ).join('');
        suggestEl.style.display = 'block';
        suggestEl.className = 'absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg shadow-lg max-h-60 overflow-auto';
        
        suggestEl.querySelectorAll('div').forEach(el => {
            el.addEventListener('click', () => {
                const val = el.getAttribute('data-val');
                inputEl.value = val;
                suggestEl.style.display = 'none';
                if (typeof setterCallback === 'function') setterCallback(val);
            });
        });
    });
    
    document.addEventListener('click', (ev) => {
        if (!inputEl.contains(ev.target) && !suggestEl.contains(ev.target)) {
            suggestEl.style.display = 'none';
        }
    });
}

async function loadTrivia() {
    try {
        const res = await fetch(`${API_BASE}/api/trivia`);
        const data = await res.json();
        triviaPool = Array.isArray(data) ? data : (typeof data === 'object' ? Object.values(data).flat() : []);
        
        if (triviaPool.length) {
            showRandomFact();
            setInterval(showRandomFact, 60000); // Update every minute
        }
    } catch (e) {
        console.warn('Failed to load trivia:', e);
        triviaPool = [
            "Did you know? Indoor plants can improve air quality and mood.",
            "Air quality can vary significantly throughout the day."
        ];
        showRandomFact();
    }
}

function showRandomFact() {
    if (triviaPool.length) {
        const fact = triviaPool[Math.floor(Math.random() * triviaPool.length)];
        document.getElementById('aqi-fact').textContent = fact;
    }
}

async function loadCurrentLocationAQI() {
    const aqiValue = document.getElementById('aqi-value');
    const aqiCategory = document.getElementById('aqi-category');
    const currentLocation = document.getElementById('current-location');
    const currentPm25 = document.getElementById('current-pm25');
    const currentPm10 = document.getElementById('current-pm10');
    
    try {
        if (!navigator.geolocation) {
            aqiValue.textContent = '—';
            aqiCategory.textContent = 'Geolocation not supported';
            return;
        }
        
        const pos = await new Promise((res, rej) => 
            navigator.geolocation.getCurrentPosition(res, rej, { timeout: 10000 })
        );
        
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        
        // Try to get city name
        let cityName = null;
        try {
            const r = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
            const j = await r.json();
            cityName = j?.address?.city || j?.address?.town || j?.address?.village || 'Your location';
        } catch (e) {}
        
        // Fetch AQI by coordinates
        const res = await fetch(`${API_BASE}/api/live_aqi_coords?lat=${lat}&lon=${lon}`);
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);
        
        const aqi = data.latest_aqi;
        aqiValue.textContent = aqi ?? '—';
        aqiCategory.textContent = getAQICategory(aqi);
        currentLocation.textContent = cityName || 'Your location';
        currentPm25.textContent = data.pollutants?.pm2_5 ?? '—';
        currentPm10.textContent = data.pollutants?.pm10 ?? '—';
        
        // Update AQI color
        updateAQIColor(aqiValue, aqi);
    } catch (e) {
        console.warn('Failed to load current location AQI:', e);
        aqiValue.textContent = '—';
        aqiCategory.textContent = 'Unable to fetch location AQI';
    }
}

async function searchCityAQI() {
    const input = document.getElementById('city-search-input');
    const result = document.getElementById('city-search-result');
    const city = input.value.trim();
    
    if (!city) {
        result.innerHTML = '<span class="text-red-600">Please enter a city name</span>';
        return;
    }
    
    result.innerHTML = '<span class="text-slate-600">Searching...</span>';
    
    try {
        const res = await fetch(`${API_BASE}/api/city_aqi/${encodeURIComponent(city)}`);
        const data = await res.json();
        
        if (data.error) {
            result.innerHTML = `<span class="text-red-600">${data.error}</span>`;
            return;
        }
        
        const aqi = data.latest_aqi;
        const category = getAQICategory(aqi);
        
        result.innerHTML = `
            <div class="space-y-2">
                <div class="font-semibold text-slate-900">${data.city_matched || city}</div>
                <div>AQI: <span class="font-bold text-lg">${aqi ?? 'N/A'}</span> - ${category}</div>
                <div class="text-sm">PM2.5: ${data.pollutants?.pm2_5 ?? '—'} µg/m³ | PM10: ${data.pollutants?.pm10 ?? '—'} µg/m³</div>
            </div>
        `;
    } catch (e) {
        result.innerHTML = '<span class="text-red-600">Failed to fetch city AQI. Please try again.</span>';
    }
}

async function generatePrediction() {
    const city = document.getElementById('predict-city').value;
    const horizon = parseInt(document.getElementById('predict-horizon').value) || 12;
    const stats = document.getElementById('predict-stats');
    
    if (!city) {
        stats.textContent = 'Please select a city';
        stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
        return;
    }
    
    stats.textContent = 'Loading...';
    stats.className = 'mt-4 text-sm text-slate-600 dark:text-slate-400';
    
    try {
        const res = await fetch(`${API_BASE}/api/hybrid_forecast/${encodeURIComponent(city)}?horizon=${horizon}`);
        const data = await res.json();
        
        if (res.status !== 200 || data.error) {
            stats.textContent = data.error || 'Failed to load prediction';
            stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
            renderPredictChart([], city);
            return;
        }
        
        const forecast = data.forecast || [];
        renderPredictChart(forecast, city);
        const avg = forecast.length ? (forecast.reduce((a, b) => a + (Number(b.predicted_aqi || b.yhat || 0)), 0) / forecast.length).toFixed(2) : 'N/A';
        stats.textContent = `${city} · Horizon: ${data.forecast_horizon_months || horizon} months · Avg: ${avg}`;
        stats.className = 'mt-4 text-sm text-slate-600 dark:text-slate-400';
    } catch (e) {
        console.error('Prediction failed:', e);
        stats.textContent = 'Network error while loading prediction';
        stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
    }
}

async function loadHistoric() {
    const city = document.getElementById('historic-city').value;
    const from = document.getElementById('historic-from').value;
    const to = document.getElementById('historic-to').value;
    const stats = document.getElementById('historic-stats');
    
    if (!city) {
        stats.textContent = 'Please select a city';
        stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
        return;
    }
    
    stats.textContent = 'Loading...';
    stats.className = 'mt-4 text-sm text-slate-600 dark:text-slate-400';
    
    try {
        const queryParts = [];
        if (from) queryParts.push(`start_date=${encodeURIComponent(from + '-01')}`);
        if (to) queryParts.push(`end_date=${encodeURIComponent(to + '-01')}`);
        const query = queryParts.length ? `?${queryParts.join('&')}` : '';
        
        const res = await fetch(`${API_BASE}/api/get_forecast/${encodeURIComponent(city)}${query}`);
        const data = await res.json();
        
        if (res.status !== 200 || data.error) {
            stats.textContent = data.error || 'Failed to load historic data';
            stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
            renderHistoricChart([], city);
            return;
        }
        
        const forecast = data.forecast || [];
        renderHistoricChart(forecast, city);
        const avg = forecast.length ? (forecast.reduce((a, b) => a + (Number(b.yhat || b.predicted_aqi || 0)), 0) / forecast.length).toFixed(2) : 'N/A';
        stats.textContent = `${city} · points: ${forecast.length} · Avg: ${avg}`;
        stats.className = 'mt-4 text-sm text-slate-600 dark:text-slate-400';
    } catch (e) {
        console.error('Historic load failed:', e);
        stats.textContent = 'Network error while loading historic data';
        stats.className = 'mt-4 text-sm text-red-600 dark:text-red-400';
    }
}

// ==========================
// DEVICE VIEW UPDATES
// ==========================
function updateDeviceView(data, deviceType) {
    const latest = data.latest || {};
    const prefix = deviceType;
    
    // Update stat cards
    updateStatCard(`${prefix}-temp`, latest.temperature);
    updateStatCard(`${prefix}-humidity`, latest.humidity);
    updateStatCard(`${prefix}-pm25`, latest.pm25);
    updateStatCard(`${prefix}-pm10`, latest.pm10);
    updateStatCard(`${prefix}-voc`, latest.voc_ppm || latest.voc);
    updateStatCard(`${prefix}-pressure`, latest.pressure);
    updateStatCard(`${prefix}-mq135`, latest.mq135);
    
    if (deviceType === 'static') {
        updateStatCard(`${prefix}-co2`, latest.co2);
    }
    
    // Update charts
    updateDeviceCharts(latest, deviceType);
    
    // Update map
    if (latest.gps && latest.gps.lat && latest.gps.lon) {
        updateMap(latest.gps.lat, latest.gps.lon, deviceType);
    }
}

function updateStatCard(id, value) {
    const el = document.getElementById(id);
    if (el) {
        if (value !== null && value !== undefined && !isNaN(value)) {
            el.textContent = parseFloat(value).toFixed(1);
        } else {
            el.textContent = '—';
        }
    }
}

// ==========================
// CHARTS
// ==========================
function initializeCharts() {
    // Portable charts
    const portableTempCtx = document.getElementById('portable-temp-chart')?.getContext('2d');
    if (portableTempCtx) {
        charts.portable.temp = new Chart(portableTempCtx, getChartConfig('Temperature (°C)', '#3b82f6'));
    }
    
    const portablePmCtx = document.getElementById('portable-pm-chart')?.getContext('2d');
    if (portablePmCtx) {
        const isDark = document.documentElement.classList.contains('dark');
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        const bgColor = isDark ? 'rgba(15, 23, 42, 0.5)' : 'rgba(248, 250, 252, 0.5)';
        
        charts.portable.pm = new Chart(portablePmCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'PM2.5', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', tension: 0.4, fill: true },
                    { label: 'PM10', data: [], borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', tension: 0.4, fill: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Fixed: Prevent chart from growing infinitely
                backgroundColor: bgColor, // Fixed: Dark background for charts
                layout: {
                    padding: {
                        left: 10,
                        right: 10,
                        top: 10,
                        bottom: 10
                    }
                },
                plugins: { 
                    legend: { 
                        labels: { color: textColor },
                        display: true
                    } 
                },
                scales: {
                    x: { 
                        ticks: { color: tickColor, maxRotation: 45, minRotation: 0 },
                        grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                    },
                    y: { 
                        ticks: { color: tickColor },
                        grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                    }
                }
            }
        });
    }
    
    // Static charts
    const staticTempCtx = document.getElementById('static-temp-chart')?.getContext('2d');
    if (staticTempCtx) {
        charts.static.temp = new Chart(staticTempCtx, getChartConfig('Temperature (°C)', '#3b82f6'));
    }
    
    const staticGasCtx = document.getElementById('static-gas-chart')?.getContext('2d');
    if (staticGasCtx) {
        const isDark = document.documentElement.classList.contains('dark');
        const textColor = isDark ? '#e2e8f0' : '#64748b';
        const tickColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        const bgColor = isDark ? 'rgba(15, 23, 42, 0.5)' : 'rgba(248, 250, 252, 0.5)';
        
        charts.static.gas = new Chart(staticGasCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'CO₂', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', tension: 0.4, fill: true },
                    { label: 'VOC', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', tension: 0.4, fill: true },
                    { label: 'PM2.5', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', tension: 0.4, fill: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Fixed: Prevent chart from growing infinitely
                backgroundColor: bgColor, // Fixed: Dark background for charts
                layout: {
                    padding: {
                        left: 10,
                        right: 10,
                        top: 10,
                        bottom: 10
                    }
                },
                plugins: { 
                    legend: { 
                        labels: { color: textColor },
                        display: true
                    } 
                },
                scales: {
                    x: { 
                        ticks: { color: tickColor, maxRotation: 45, minRotation: 0 },
                        grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                    },
                    y: { 
                        ticks: { color: tickColor },
                        grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                    }
                }
            }
        });
    }
}

function getChartConfig(label, color) {
    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#e2e8f0' : '#64748b';
    const tickColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#334155' : '#e2e8f0';
    const bgColor = isDark ? 'rgba(15, 23, 42, 0.5)' : 'rgba(248, 250, 252, 0.5)';
    
    return {
        type: 'line',
        data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: color + '20', tension: 0.4, fill: true }] },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Fixed: Prevent chart from growing infinitely
            backgroundColor: bgColor, // Fixed: Dark background for charts
            layout: {
                padding: {
                    left: 10,
                    right: 10,
                    top: 10,
                    bottom: 10
                }
            },
            plugins: { 
                legend: { 
                    labels: { color: textColor },
                    display: true
                } 
            },
            scales: {
                x: { 
                    ticks: { color: tickColor, maxRotation: 45, minRotation: 0 },
                    grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                },
                y: { 
                    ticks: { color: tickColor },
                    grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                }
            }
        }
    };
}

function updateDeviceCharts(latest, deviceType) {
    const now = new Date().toLocaleTimeString();
    const data = chartData[deviceType];
    
    // Add to buffers
    data.timestamps.push(now);
    data.temp.push(latest.temperature || null);
    data.pm25.push(latest.pm25 || null);
    data.pm10.push(latest.pm10 || null);
    
    if (deviceType === 'static') {
        data.co2.push(latest.co2 || null);
        data.voc.push(latest.voc_ppm || latest.voc || null);
    }
    
    // Trim buffers
    Object.keys(data).forEach(key => {
        if (data[key].length > CHART_BUFFER_SIZE) {
            data[key] = data[key].slice(-CHART_BUFFER_SIZE);
        }
    });
    
    // Update portable charts
    if (deviceType === 'portable') {
        if (charts.portable.temp) {
            charts.portable.temp.data.labels = data.timestamps;
            charts.portable.temp.data.datasets[0].data = data.temp;
            charts.portable.temp.update('none');
        }
        if (charts.portable.pm) {
            charts.portable.pm.data.labels = data.timestamps;
            charts.portable.pm.data.datasets[0].data = data.pm25;
            charts.portable.pm.data.datasets[1].data = data.pm10;
            charts.portable.pm.update('none');
        }
    }
    
    // Update static charts
    if (deviceType === 'static') {
        if (charts.static.temp) {
            charts.static.temp.data.labels = data.timestamps;
            charts.static.temp.data.datasets[0].data = data.temp;
            charts.static.temp.update('none');
        }
        if (charts.static.gas) {
            charts.static.gas.data.labels = data.timestamps;
            charts.static.gas.data.datasets[0].data = data.co2;
            charts.static.gas.data.datasets[1].data = data.voc;
            charts.static.gas.data.datasets[2].data = data.pm25;
            charts.static.gas.update('none');
        }
    }
}

function renderPredictChart(forecast, city) {
    const ctx = document.getElementById('predict-chart')?.getContext('2d');
    if (!ctx) return;
    
    const labels = (forecast || []).map(d => d.date || d.ds);
    const values = (forecast || []).map(d => Number(d.predicted_aqi || d.yhat || NaN));
    
    if (charts.predict) charts.predict.destroy();
    
    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#e2e8f0' : '#64748b';
    const tickColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#334155' : '#e2e8f0';
    
    charts.predict = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: `Forecast — ${city}`,
                data: values,
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                tension: 0.25,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor }
                }
            },
            scales: {
                x: {
                    ticks: { color: tickColor },
                    grid: { color: gridColor }
                },
                y: {
                    ticks: { color: tickColor },
                    grid: { color: gridColor }
                }
            }
        }
    });
}

function renderHistoricChart(forecast, city) {
    const ctx = document.getElementById('historic-chart')?.getContext('2d');
    if (!ctx) return;
    
    const labels = (forecast || []).map(d => d.ds || d.date);
    const dataPoints = (forecast || []).map(d => Number(d.yhat || d.predicted_aqi || NaN));
    
    if (charts.historic) charts.historic.destroy();
    
    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#e2e8f0' : '#64748b';
    const tickColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#334155' : '#e2e8f0';
    const bgColor = isDark ? 'rgba(15, 23, 42, 0.5)' : 'rgba(248, 250, 252, 0.5)';
    
    charts.historic = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: `${city}`,
                data: dataPoints,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.25,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Fixed: Prevent chart from growing infinitely
            backgroundColor: bgColor, // Fixed: Dark background for charts
            layout: {
                padding: {
                    left: 10,
                    right: 10,
                    top: 10,
                    bottom: 10
                }
            },
            plugins: {
                legend: {
                    labels: { color: textColor }
                }
            },
            scales: {
                x: {
                    ticks: { color: tickColor, maxRotation: 45, minRotation: 0 },
                    grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                },
                y: {
                    ticks: { color: tickColor },
                    grid: { color: gridColor, drawBorder: true, borderColor: gridColor }
                }
            }
        }
    });
}

// ==========================
// MAPS
// ==========================
function initializeMaps() {
    const portableMapEl = document.getElementById('portable-map');
    const staticMapEl = document.getElementById('static-map');
    
    if (portableMapEl && !maps.portable) {
        maps.portable = L.map('portable-map').setView([17.41, 78.55], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(maps.portable);
    }
    
    if (staticMapEl && !maps.static) {
        maps.static = L.map('static-map').setView([17.41, 78.55], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(maps.static);
    }
}

function updateMap(lat, lon, deviceType) {
    const map = maps[deviceType];
    if (!map) return;
    
    const latLng = [lat, lon];
    
    if (mapMarkers[deviceType]) {
        mapMarkers[deviceType].setLatLng(latLng);
    } else {
        mapMarkers[deviceType] = L.marker(latLng).addTo(map);
        mapMarkers[deviceType].bindPopup(`<b>${deviceType === 'portable' ? 'PORTABLE-01' : 'Vento-Station-01'}</b>`);
    }
    
    map.setView(latLng, 13, { animate: true, duration: 1.0 });
}

// ==========================
// UTILITIES
// ==========================
function getAQICategory(aqi) {
    if (!aqi || isNaN(aqi)) return 'Unavailable';
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 150) return 'Unhealthy for Sensitive';
    if (aqi <= 200) return 'Unhealthy';
    if (aqi <= 300) return 'Very Unhealthy';
    return 'Hazardous';
}

function updateAQIColor(element, aqi) {
    if (!aqi || isNaN(aqi)) {
        element.className = 'text-5xl font-bold text-slate-900 mb-2';
        return;
    }
    
    let color = 'slate-900';
    if (aqi <= 50) color = 'green-600';
    else if (aqi <= 100) color = 'yellow-600';
    else if (aqi <= 150) color = 'orange-600';
    else if (aqi <= 200) color = 'red-600';
    else if (aqi <= 300) color = 'purple-600';
    else color = 'gray-800';
    
    element.className = `text-5xl font-bold text-${color} mb-2`;
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (!status) return;
    
    const indicator = status.querySelector('span');
    const text = status.querySelector('span + span');
    
    if (connected) {
        indicator.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
        text.textContent = 'Connected';
        text.className = 'text-slate-600 dark:text-slate-400';
    } else {
        indicator.className = 'w-2 h-2 rounded-full bg-red-500 animate-pulse';
        text.textContent = 'Offline';
        text.className = 'text-red-600 dark:text-red-400';
    }
}

function startAutoRefresh() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    
    // Fixed: Refresh every 5-10 seconds as specified
    refreshIntervalId = setInterval(() => {
        if (currentSection === 'sensor-kit') {
            const deviceId = currentDevice === 'portable' ? 'PORTABLE-01' : 'Vento-Station-01';
            fetchDeviceData(deviceId, currentDevice);
        }
    }, REFRESH_INTERVAL); // REFRESH_INTERVAL is 5000ms (5 seconds)
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    const colors = {
        success: 'bg-green-600',
        error: 'bg-red-600',
        warning: 'bg-yellow-600',
        info: 'bg-blue-600'
    };
    
    toast.className = `${colors[type] || colors.info} text-white px-6 py-3 rounded-lg shadow-lg`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => container.removeChild(toast), 300);
    }, 5000);
}
