// Mock data for Vento Aureo - 200 cities worldwide
// Realistic AQI values and pollutant data

const MOCK_CITIES = [
    // Asia
    "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu", "Wuhan", "Hangzhou", "Xi'an", "Nanjing", "Tianjin",
    "Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kawasaki", "Hiroshima",
    "Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Ulsan", "Suwon", "Changwon", "Seongnam",
    "Bangkok", "Chiang Mai", "Phuket", "Pattaya", "Hat Yai", "Nakhon Ratchasima", "Udon Thani", "Khon Kaen",
    "Singapore", "Kuala Lumpur", "Penang", "Johor Bahru", "Ipoh", "Malacca", "Petaling Jaya", "Shah Alam",
    "Jakarta", "Surabaya", "Bandung", "Medan", "Semarang", "Makassar", "Palembang", "Tangerang",
    "Manila", "Quezon City", "Davao", "Cebu", "Zamboanga", "Antipolo", "Pasig", "Taguig",
    "Hanoi", "Ho Chi Minh City", "Da Nang", "Haiphong", "Can Tho", "Bien Hoa", "Nha Trang", "Hue",
    "Dhaka", "Chittagong", "Khulna", "Rajshahi", "Sylhet", "Rangpur", "Barisal", "Comilla",

    // Europe
    "London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Edinburgh", "Bristol",
    "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier",
    "Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Dusseldorf", "Dortmund",
    "Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Malaga", "Murcia", "Palma",
    "Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa", "Bologna", "Florence",
    "Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Tilburg", "Groningen", "Almere",
    "Brussels", "Antwerp", "Ghent", "Charleroi", "Liege", "Bruges", "Namur", "Leuven",
    "Vienna", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt", "Villach", "Wels",

    // Americas
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
    "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte", "San Francisco",
    "Seattle", "Denver", "Washington DC", "Boston", "Nashville", "Detroit", "Portland", "Las Vegas",
    "Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City",
    "Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Leon", "Juarez", "Zapopan",
    "Sao Paulo", "Rio de Janeiro", "Brasilia", "Salvador", "Fortaleza", "Belo Horizonte", "Manaus", "Curitiba",
    "Buenos Aires", "Cordoba", "Rosario", "Mendoza", "La Plata", "Mar del Plata", "Salta", "Santa Fe",

    // Middle East & Africa
    "Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Al Ain", "Umm Al Quwain",
    "Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Buraidah",
    "Cairo", "Alexandria", "Giza", "Shubra El Kheima", "Port Said", "Suez", "Luxor", "Aswan",
    "Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Gaziantep", "Konya", "Antalya",
    "Tel Aviv", "Jerusalem", "Haifa", "Rishon LeZion", "Petah Tikva", "Ashdod", "Netanya", "Beersheba",

    // Oceania
    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Newcastle",
    "Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Palmerston North", "Napier"
];

// Generate realistic AQI value based on city characteristics
function generateRealisticAQI(city, date = new Date()) {
    const month = date.getMonth();
    const hour = date.getHours();

    // Base AQI by region (realistic patterns)
    const baseAQI = {
        // High pollution cities
        "Delhi": 180, "Beijing": 150, "Dhaka": 170, "Lahore": 160, "Cairo": 140,
        "Mumbai": 120, "Shanghai": 130, "Jakarta": 110, "Kolkata": 140, "Karachi": 150,

        // Moderate pollution
        "Bangkok": 90, "Mexico City": 85, "Istanbul": 80, "Los Angeles": 75, "Seoul": 70,
        "Tokyo": 60, "Paris": 65, "London": 55, "Rome": 70, "Madrid": 65,

        // Low pollution (default for unlisted cities)
        "default": 45
    };

    let aqi = baseAQI[city] || baseAQI["default"];

    // Seasonal variation (winter worse in many cities)
    if (month >= 10 || month <= 2) {
        aqi *= 1.3; // Winter increase
    } else if (month >= 5 && month <= 8) {
        aqi *= 0.9; // Summer decrease
    }

    // Time of day variation (rush hours worse)
    if (hour >= 7 && hour <= 9 || hour >= 17 && hour <= 19) {
        aqi *= 1.2; // Rush hour increase
    } else if (hour >= 2 && hour <= 5) {
        aqi *= 0.8; // Early morning decrease
    }

    // Add some randomness (±15%)
    aqi *= (0.85 + Math.random() * 0.3);

    return Math.round(Math.max(10, Math.min(500, aqi)));
}

// Generate PM2.5 from AQI
function aqiToPM25(aqi) {
    // Approximate conversion
    if (aqi <= 50) return Math.round(aqi * 0.24);
    if (aqi <= 100) return Math.round(12 + (aqi - 50) * 0.7);
    if (aqi <= 150) return Math.round(35.5 + (aqi - 100) * 0.9);
    if (aqi <= 200) return Math.round(55.5 + (aqi - 150) * 1.5);
    if (aqi <= 300) return Math.round(150.5 + (aqi - 200) * 1.0);
    return Math.round(250.5 + (aqi - 300) * 0.5);
}

// Generate PM10 from AQI (typically higher than PM2.5)
function aqiToPM10(aqi) {
    return Math.round(aqiToPM25(aqi) * 1.6);
}

// Generate historic data for a city
function generateHistoricData(city, startDate, endDate, monthlyOnly = true) {
    const data = [];
    const start = new Date(startDate || '2020-01-01');
    const end = new Date(endDate || '2024-11-30');

    let current = new Date(start);

    while (current <= end) {
        const aqi = generateRealisticAQI(city, current);
        data.push({
            ds: current.toISOString().split('T')[0],
            date: current.toISOString().split('T')[0],
            yhat: aqi,
            predicted_aqi: aqi,
            yhat_lower: Math.round(aqi * 0.85),
            yhat_upper: Math.round(aqi * 1.15)
        });

        // Move to next month
        if (monthlyOnly) {
            current.setMonth(current.getMonth() + 1);
        } else {
            current.setDate(current.getDate() + 1);
        }
    }

    return data;
}

// Generate prediction data for a city
function generatePredictionData(city, horizonMonths = 12) {
    const data = [];
    const start = new Date('2024-12-01'); // Start from Dec 2024

    for (let i = 0; i < horizonMonths; i++) {
        const date = new Date(start);
        date.setMonth(start.getMonth() + i);

        const aqi = generateRealisticAQI(city, date);

        data.push({
            date: date.toISOString().split('T')[0],
            ds: date.toISOString().split('T')[0],
            predicted_aqi: aqi,
            yhat: aqi,
            yhat_lower: Math.round(aqi * 0.80),
            yhat_upper: Math.round(aqi * 1.20)
        });
    }

    return data;
}

// Generate short-term forecast (daily)
function generateShortTermData(city, days = 7) {
    const data = [];
    const start = new Date();

    for (let i = 0; i < days; i++) {
        const date = new Date(start);
        date.setDate(start.getDate() + i);

        const aqi = generateRealisticAQI(city, date);

        data.push({
            date: date.toISOString().split('T')[0],
            predicted_aqi: aqi,
            yhat: aqi,
            value: aqi
        });
    }

    return data;
}

// Get current AQI for a city
function getCurrentCityAQI(city) {
    const aqi = generateRealisticAQI(city, new Date());
    const pm25 = aqiToPM25(aqi);
    const pm10 = aqiToPM10(aqi);

    return {
        city_requested: city,
        city_matched: city,
        latest_aqi: aqi,
        pollutants: {
            pm2_5: pm25,
            pm10: pm10
        },
        source: "mock-data"
    };
}

// Get trivia facts
const TRIVIA_FACTS = [
    "Did you know? Indoor plants like Peace Lily can remove several common indoor pollutants.",
    "Air quality can vary significantly throughout the day, with rush hours typically showing higher pollution.",
    "PM2.5 particles are so small they can penetrate deep into your lungs and even enter your bloodstream.",
    "The WHO estimates that air pollution causes 7 million premature deaths worldwide every year.",
    "Trees act as natural air filters, removing pollutants and producing oxygen.",
    "Indoor air can be 2-5 times more polluted than outdoor air in some cases.",
    "Regular exercise improves your body's ability to process oxygen, even in polluted environments.",
    "Air purifiers with HEPA filters can remove 99.97% of particles as small as 0.3 microns.",
    "Cooking with gas stoves can significantly increase indoor air pollution levels.",
    "Opening windows during low-pollution hours can help improve indoor air quality.",
    "Wearing N95 masks can filter out 95% of airborne particles, including PM2.5.",
    "Electric vehicles produce zero direct emissions, helping reduce urban air pollution.",
    "Green roofs and vertical gardens can significantly improve air quality in cities.",
    "Air quality tends to be better after rainfall, as rain washes pollutants from the air.",
    "Children are more vulnerable to air pollution due to their developing respiratory systems.",
    "Reducing meat consumption can indirectly improve air quality by reducing agricultural emissions.",
    "Smart city initiatives using IoT sensors can help monitor and manage air quality in real-time.",
    "Bamboo grows quickly and absorbs more CO2 than many tree species, making it excellent for air quality.",
    "Air pollution can affect cognitive function and has been linked to decreased academic performance.",
    "The cleanest air in the world is typically found in remote areas like Antarctica and the Amazon rainforest."
];

function getRandomTrivia() {
    return TRIVIA_FACTS[Math.floor(Math.random() * TRIVIA_FACTS.length)];
}

// Generate realistic sensor data
function generateSensorData(deviceId) {
    const isPortable = deviceId.includes('PORTABLE');
    const now = new Date();

    // Base values
    const temp = 25 + Math.random() * 5;
    const humidity = 40 + Math.random() * 20;
    const pm25 = 15 + Math.random() * 30;
    const pm10 = pm25 * (1.5 + Math.random() * 0.5);

    const latest = {
        timestamp: now.toISOString(),
        temperature: temp.toFixed(1),
        humidity: humidity.toFixed(1),
        pm2_5: pm25.toFixed(1),
        pm10: pm10.toFixed(1),
        pressure: (1013 + Math.random() * 10).toFixed(0),
        mq135_raw: (150 + Math.random() * 50).toFixed(0)
    };

    if (isPortable) {
        latest.voc_index = (50 + Math.random() * 100).toFixed(0);
    } else {
        latest.co2 = (400 + Math.random() * 200).toFixed(0);
        latest.voc = (0.5 + Math.random() * 0.5).toFixed(2);
    }

    // Generate chart history (last 20 points)
    const chart = [];
    for (let i = 19; i >= 0; i--) {
        const t = new Date(now.getTime() - i * 5000); // 5 sec intervals
        const point = {
            timestamp: t.toISOString(),
            temperature: (temp + (Math.random() - 0.5)).toFixed(1),
            humidity: (humidity + (Math.random() - 0.5)).toFixed(1),
            pm2_5: (pm25 + (Math.random() * 5 - 2.5)).toFixed(1),
            pm10: (pm10 + (Math.random() * 5 - 2.5)).toFixed(1)
        };

        if (isPortable) {
            point.voc_index = (Number(latest.voc_index) + (Math.random() * 10 - 5)).toFixed(0);
        } else {
            point.co2 = (Number(latest.co2) + (Math.random() * 20 - 10)).toFixed(0);
            point.voc = (Number(latest.voc) + (Math.random() * 0.1 - 0.05)).toFixed(2);
        }
        chart.push(point);
    }

    return {
        device_id: deviceId,
        status: 'ok',
        latest: latest,
        chart: chart
    };
}

// Export for use in app
window.MOCK_DATA = {
    cities: MOCK_CITIES,
    generateHistoricData,
    generatePredictionData,
    generateShortTermData,
    getCurrentCityAQI,
    getRandomTrivia,
    generateRealisticAQI,
    aqiToPM25,
    aqiToPM10,
    generateSensorData
};
