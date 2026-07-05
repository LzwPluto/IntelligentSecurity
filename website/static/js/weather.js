// Weather widget - 自动刷新 + 城市设置

const weatherIcons = {
    '晴': 'bi-sun', '多云': 'bi-cloud-sun', '阴': 'bi-clouds',
    '小雨': 'bi-cloud-drizzle', '中雨': 'bi-cloud-rain', '大雨': 'bi-cloud-rain-heavy',
    '暴雨': 'bi-cloud-rain-heavy', '雪': 'bi-cloud-snow', '阵雨': 'bi-cloud-rain',
    '雷阵雨': 'bi-cloud-lightning', '雾': 'bi-cloud-fog2', '霾': 'bi-cloud-haze2',
    '沙尘暴': 'bi-wind', '雷阵雨并伴有冰雹': 'bi-cloud-lightning',
};

function getWeatherIcon(text) {
    if (!text) return 'bi-cloud';
    for (const [key, icon] of Object.entries(weatherIcons)) {
        if (text.includes(key)) return icon;
    }
    return 'bi-cloud';
}

let currentLocation = '';

async function loadWeather() {
    const container = document.getElementById('weather-widget');
    if (!container) return;

    try {
        const [currentResp, forecastResp, locResp] = await Promise.all([
            fetch('/weather/api/current'),
            fetch('/weather/api/forecast'),
            fetch('/weather/api/location')
        ]);

        const current = await currentResp.json();
        const forecast = await forecastResp.json();
        const locData = await locResp.json();
        currentLocation = locData.location || '';

        if (current.error) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-cloud-slash" style="font-size: 2rem;"></i>
                    <p class="mt-2">${current.error}</p>
                </div>`;
            return;
        }

        const icon = getWeatherIcon(current.text);

        let forecastHtml = '';
        if (forecast.forecast) {
            forecastHtml = forecast.forecast.map(day => `
                <div class="weather-forecast-item">
                    <span class="text-muted">${day.date.slice(5)}</span>
                    <span>${day.text_day}</span>
                    <span><strong>${day.high}°</strong> / ${day.low}°</span>
                </div>
            `).join('');
        }

        container.innerHTML = `
            <div class="weather-current">
                <div class="weather-icon">
                    <i class="bi ${icon}"></i>
                </div>
                <div class="weather-temp">${current.temperature}°C</div>
                <div class="text-muted mb-1">${current.location} · ${current.text}</div>
                <div class="small text-muted">
                    湿度 ${current.humidity}% · 风速 ${current.wind_speed} km/h
                </div>
            </div>
            <hr class="my-2">
            <div class="mt-2">
                <small class="text-muted fw-bold">未来预报</small>
                ${forecastHtml}
            </div>
            <div class="mt-2 pt-2 border-top">
                <div class="input-group input-group-sm">
                    <input type="text" class="form-control" id="weather-city-input"
                           placeholder="输入城市名" value="${currentLocation}">
                    <button class="btn btn-outline-primary" type="button" onclick="changeWeatherCity()">
                        <i class="bi bi-geo-alt"></i> 切换
                    </button>
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="bi bi-wifi-off" style="font-size: 2rem;"></i>
                <p class="mt-2">天气服务连接失败</p>
            </div>`;
    }
}

async function changeWeatherCity() {
    const input = document.getElementById('weather-city-input');
    if (!input) return;
    const city = input.value.trim();
    if (!city) return;

    try {
        const resp = await fetch('/weather/api/location', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({location: city})
        });
        const data = await resp.json();
        if (data.message) {
            // 刷新天气显示
            loadWeather();
        }
    } catch (e) {
        console.error('Failed to change city:', e);
    }
}

// Enter 键提交
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.id === 'weather-city-input') {
        changeWeatherCity();
    }
});

// 初始加载
loadWeather();

// 每 15 分钟自动刷新
setInterval(loadWeather, 15 * 60 * 1000);
