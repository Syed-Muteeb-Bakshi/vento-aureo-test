# 🌟 Vento Aureo – Air Quality Intelligence Platform

> Real-time air quality monitoring, predictive analytics, and IoT sensor visualization

## 📋 Overview

Vento Aureo is a comprehensive Air Quality Intelligence Platform featuring:
- **Real-time Dashboard** with current location AQI and city search
- **IoT Sensor Kit Monitoring** for portable and static devices
- **Predictive AQI Analysis** using machine learning models
- **Historic AQI Charts** with customizable date ranges
- **Cozy, modern UI** with smooth animations and responsive design

## 🚀 Quick Start

### Option 1: Open Directly

1. Clone the repository:
   ```bash
   git clone https://github.com/Syed-Muteeb-Bakshi/vento-aureo-test.git
   cd vento-aureo-test/frontend
   ```

2. Open `index.html` in your browser (some features require a local server due to CORS)

### Option 2: Local Server (Recommended)

#### Using Node.js
```bash
cd frontend
node demo-server.js
```
Then open: `http://localhost:8080`

#### Using Python
```bash
cd frontend
python -m http.server 8080
```

#### Using PHP
```bash
cd frontend
php -S localhost:8080
```

## ✨ Features

### Title Screen
- Elegant fade-in animation with floating symbols
- Smooth transition to main dashboard

### Dashboard Section
- **Current Location AQI**: Automatically detects your location and displays real-time AQI
- **City Search**: Look up AQI for any supported city
- **AQI Classification**: Visual guide to AQI categories (Good, Moderate, Unhealthy, etc.)
- **Random AQI Facts**: Rotating educational facts about air quality

### Sensor Kit Section
- **Portable Sensor**: Real-time monitoring of portable IoT device
  - Temperature, Humidity, Pressure
  - PM2.5, PM10, VOC levels
  - MQ135 sensor readings
  - Interactive charts and GPS map
- **Static Station**: Monitoring for fixed installation
  - All portable features plus CO₂ monitoring
  - Separate charts and location tracking

### Predictive AQI Analysis
- Long-range forecasts (1-60 months)
- Hybrid ML model predictions
- Interactive charts with city selection

### Historic AQI Charts
- Monthly historical data visualization
- Customizable date range filters
- Multiple chart types (line, bar, area)

## ⚙️ Configuration

### API Configuration

Edit `app.js` (lines 8-10):

```javascript
const API_BASE = "https://vento-backend-678919375946.us-east1.run.app";
const API_KEY = "YOUR_API_KEY_HERE"; // Optional, for authenticated endpoints
const REFRESH_INTERVAL = 5000; // Auto-refresh interval in milliseconds
```

### API Endpoints Used

- `/api/list_cities` - Get list of supported cities
- `/api/live_aqi_coords?lat={lat}&lon={lon}` - Get AQI by coordinates
- `/api/city_aqi/{city}` - Get AQI for a specific city
- `/api/visual_report?device_id={device_id}` - Get sensor data for IoT devices
- `/api/hybrid_forecast/{city}?horizon={months}` - Get predictive forecast
- `/api/get_forecast/{city}` - Get historic data
- `/api/trivia` - Get random AQI facts

## 🎨 Design Philosophy

The dashboard features a **cozy, mature design** with:
- Clean, professional color scheme (slate/blue palette)
- Smooth animations and transitions
- Mobile-first responsive layout
- Accessible UI with proper ARIA labels
- Sidebar navigation (YouTube-style)

## 📱 Mobile Support

Fully responsive design:
- **Mobile**: Collapsible sidebar, stacked layouts
- **Tablet**: Optimized grid layouts
- **Desktop**: Full sidebar, multi-column grids

## 🔐 API Key Setup

### Development
Use placeholder `YOUR_API_KEY_HERE` for local testing. The dashboard will automatically fall back to mock data if the API is unreachable.

### Production
**⚠️ Never hardcode API keys in frontend code.**

**Recommended**: Use a server-side proxy:
1. Create a serverless function (Vercel/Netlify/Cloud Run)
2. Proxy requests from frontend to backend
3. Inject API key server-side
4. Return responses to frontend

## 🧪 Testing

### Test with Mock Data
Mock data files are in `example_payloads/`:
- `portable.json` - Sample data for PORTABLE-01
- `static.json` - Sample data for Vento-Station-01

The dashboard automatically uses mock data if the API is unreachable.

### Test with Real Backend
1. Ensure backend is running at configured `API_BASE`
2. Test sensor upload:
   ```bash
   curl -X POST "https://vento-backend-678919375946.us-east1.run.app/api/upload_sensor" \
     -H "Content-Type: application/json" \
     -H "x-api-key: YOUR_API_KEY_HERE" \
     -d '{
       "device_id": "PORTABLE-01",
       "city": "Hyderabad",
       "sensors": {
         "pm25": 15,
         "pm10": 25,
         "temperature": 28.5,
         "humidity": 60,
         "pressure": 1013,
         "voc_ppm": 130,
         "mq135": 1900
       },
       "gps": {
         "lat": 17.41,
         "lon": 78.55
       }
     }'
   ```
3. Dashboard will show new data within 5 seconds (one refresh cycle)

## 🌐 CORS Configuration

If you encounter CORS errors, ensure your backend sets:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, x-api-key, Authorization
```

For Flask:
```python
from flask_cors import CORS
CORS(app)
```

## 📦 Deployment

### Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. In `frontend/` directory: `vercel`
3. Follow prompts

### Netlify
1. Drag and drop `frontend/` folder to [Netlify Drop](https://app.netlify.com/drop)
2. Or use CLI: `netlify deploy --dir=frontend`

### GitHub Pages
1. Push code to GitHub
2. Enable GitHub Pages in repository settings
3. Set source to `/frontend` directory

## 🐛 Troubleshooting

### Charts Not Updating
- Check browser console for errors
- Verify API response format
- Ensure Chart.js CDN loaded

### Map Not Showing
- Check Leaflet CDN loaded
- Verify GPS coordinates are valid
- Check browser console for errors

### Mock Data Not Loading
- Ensure you're running a local server (not file://)
- Check that `example_payloads/` directory exists
- Verify JSON files are valid

### API Errors
- Check network tab in DevTools
- Verify `API_BASE` URL is correct
- Check CORS headers
- Try mock data fallback

## 📊 Data Fields

| Field | Unit | Description | Available On |
|-------|------|-------------|--------------|
| Temperature | °C | Ambient temperature | Both devices |
| Humidity | % | Relative humidity | Both devices |
| Pressure | hPa | Atmospheric pressure | Both devices |
| PM2.5 | µg/m³ | Fine particulate matter | Both devices |
| PM10 | µg/m³ | Coarse particulate matter | Both devices |
| CO₂ | ppm | Carbon dioxide | Static only |
| VOC | ppm | Volatile organic compounds | Both devices |
| MQ135 | raw | Gas sensor raw value | Both devices |
| GPS | lat/lon | Device coordinates | Both devices |

## 🔧 Customization

### Change Refresh Interval
Edit `app.js`:
```javascript
const REFRESH_INTERVAL = 10000; // 10 seconds
```

### Change Chart Buffer Size
Edit `app.js`:
```javascript
const CHART_BUFFER_SIZE = 30; // Show last 30 points
```

### Modify Color Scheme
Edit `style.css` and Tailwind classes in `index.html` to match your brand colors.

## 📄 License

This project is part of the Vento Aureo Air Quality Platform.

## 🙏 Acknowledgments

- **Chart.js** for beautiful, responsive charts
- **Leaflet** for interactive maps
- **Tailwind CSS** for utility-first styling
- **OpenStreetMap** for map tiles

---

**Welcome to Vento Aureo** 🌬️  
*Breathe better, live better.*
