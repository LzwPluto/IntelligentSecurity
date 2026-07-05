// Dashboard - Real-time sensor updates, connection status, and mini chart

const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity
});

// Thresholds (loaded from server)
let thresholds = {
    temperature: {high: 35, low: 10},
    humidity: {high: 80, low: 20},
    smoke: {high: 300}
};

fetch('/sensor/api/thresholds')
    .then(r => r.json())
    .then(data => { thresholds = data; })
    .catch(e => console.warn('Failed to load thresholds:', e));

// Sensor display config
const sensorConfig = {
    temperature: {unit: '℃', elem: 'temp-value', timeElem: 'temp-time', statusElem: 'temp-status'},
    humidity: {unit: '%', elem: 'humidity-value', timeElem: 'humidity-time', statusElem: 'humidity-status'},
    smoke: {unit: 'ppm', elem: 'smoke-value', timeElem: 'smoke-time', statusElem: 'smoke-status'}
};

// Chart colors
const chartColors = {
    temperature: {border: 'rgb(220, 53, 69)', bg: 'rgba(220, 53, 69, 0.1)'},
    humidity: {border: 'rgb(13, 110, 253)', bg: 'rgba(13, 110, 253, 0.1)'},
    smoke: {border: 'rgb(255, 193, 7)', bg: 'rgba(255, 193, 7, 0.1)'}
};

let realtimeChart = null;
let currentRange = '1h';
const maxRealtimePoints = 60;

// 每个数据点的最小宽度(px), 用于计算可滚动图表宽度
const pxPerPoint = {1: 8, '1h': 8, '6h': 6, '24h': 4, '7d': 3, '30d': 2};

function initChart() {
    const ctx = document.getElementById('realtimeChart');
    if (!ctx) return;

    realtimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '温度',
                    data: [],
                    borderColor: chartColors.temperature.border,
                    backgroundColor: chartColors.temperature.bg,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    yAxisID: 'y'
                },
                {
                    label: '湿度',
                    data: [],
                    borderColor: chartColors.humidity.border,
                    backgroundColor: chartColors.humidity.bg,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    yAxisID: 'y'
                },
                {
                    label: '烟雾',
                    data: [],
                    borderColor: chartColors.smoke.border,
                    backgroundColor: chartColors.smoke.bg,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            animation: false,
            interaction: {mode: 'index', intersect: false},
            plugins: {
                legend: {display: false},
                tooltip: {enabled: true}
            },
            layout: {padding: 0},
            scales: {
                x: {
                    display: false,
                    grid: {display: false}
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    display: false,
                    grid: {display: true, color: 'rgba(0,0,0,0.06)'},
                    ticks: {display: false},
                    title: {display: false}
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    display: false,
                    grid: {drawOnChartArea: false},
                    ticks: {display: false},
                    title: {display: false}
                }
            }
        }
    });
}

// ---- DOM-based fixed axes ----

function niceScale(min, max, maxTicks) {
    if (min === max) { min -= 1; max += 1; }
    const range = max - min;
    const roughStep = range / (maxTicks - 1);
    const mag = Math.pow(10, Math.floor(Math.log10(roughStep)));
    const norm = roughStep / mag;
    let step;
    if (norm <= 1.5) step = 1 * mag;
    else if (norm <= 3) step = 2 * mag;
    else if (norm <= 7) step = 5 * mag;
    else step = 10 * mag;
    const niceMin = Math.floor(min / step) * step;
    const niceMax = Math.ceil(max / step) * step;
    const ticks = [];
    for (let v = niceMin; v <= niceMax + step * 0.5; v += step) {
        ticks.push(Math.round(v * 1000) / 1000);
    }
    return ticks;
}

function updateYAxis() {
    const panel = document.getElementById('y-axis-panel');
    if (!panel || !realtimeChart) return;

    const ds = realtimeChart.data.datasets;
    const tempData = ds[0].data.filter(v => v !== null);
    const humData = ds[1].data.filter(v => v !== null);
    const smokeData = ds[2].data.filter(v => v !== null);

    // 左Y轴: 温度+湿度
    let leftTicks = [];
    if (tempData.length || humData.length) {
        const allLeft = [...tempData, ...humData];
        leftTicks = niceScale(Math.min(...allLeft), Math.max(...allLeft), 6);
    }
    // 右Y轴: 烟雾
    let rightTicks = [];
    if (smokeData.length) {
        rightTicks = niceScale(Math.min(...smokeData), Math.max(...smokeData), 6);
    }

    // 用左Y轴的刻度渲染DOM标签
    const labels = leftTicks.slice().reverse();
    panel.innerHTML = labels.map((v, i) => {
        const isLast = i === labels.length - 1;
        return `<span class="y-axis-label">${isLast ? '温度℃/湿度%' : v}</span>`;
    }).join('');
}

function updateXAxis() {
    const labelsEl = document.getElementById('x-axis-labels');
    if (!labelsEl || !realtimeChart) return;

    const wrapper = document.getElementById('chart-scroll-wrapper');
    const labels = realtimeChart.data.labels;
    if (!labels.length) { labelsEl.innerHTML = ''; return; }

    const canvas = document.getElementById('realtimeChart');
    const canvasWidth = canvas.width;
    const wrapperWidth = wrapper.clientWidth;
    const pp = pxPerPoint[currentRange] || 8;
    const totalWidth = Math.max(labels.length * pp, wrapperWidth);

    // 计算当前可见区域对应的数据索引
    const scrollRatio = wrapper.scrollLeft / Math.max(totalWidth - wrapperWidth, 1);
    const visibleCount = Math.floor(wrapperWidth / pp);
    const startIdx = Math.round(scrollRatio * Math.max(labels.length - visibleCount, 0));
    const endIdx = Math.min(startIdx + visibleCount, labels.length - 1);

    // 采样可见标签
    const maxLabels = 8;
    const visibleLabels = [];
    const step = Math.max(1, Math.floor((endIdx - startIdx) / (maxLabels - 1)));
    for (let i = startIdx; i <= endIdx; i += step) {
        visibleLabels.push(labels[i]);
    }
    if (visibleLabels.length && visibleLabels[visibleLabels.length - 1] !== labels[endIdx]) {
        visibleLabels.push(labels[endIdx]);
    }

    labelsEl.innerHTML = visibleLabels.map(l => `<span>${l}</span>`).join('');

    // 同步X轴容器位置
    labelsEl.style.left = (65 + wrapper.scrollLeft) + 'px';
    labelsEl.style.width = wrapperWidth + 'px';
}

// 调整图表容器宽度以支持滚动
function adjustChartWidth(dataCount) {
    const wrapper = document.getElementById('chart-scroll-wrapper');
    const canvas = document.getElementById('realtimeChart');
    const hint = document.getElementById('chart-scroll-hint');
    if (!wrapper || !canvas) return;

    const parentWidth = wrapper.parentElement.clientWidth - 65; // 减去Y轴面板宽度

    if (currentRange === '1h' || dataCount <= 30) {
        // 1h模式或数据少: 自适应宽度, 不滚动
        canvas.style.width = parentWidth + 'px';
        canvas.width = parentWidth;
        wrapper.style.overflowX = 'hidden';
        if (hint) hint.style.display = 'none';
    } else {
        // 长时间段: 根据数据点数计算宽度
        const pp = pxPerPoint[currentRange] || 4;
        const chartWidth = Math.max(dataCount * pp, parentWidth);
        canvas.style.width = chartWidth + 'px';
        canvas.width = chartWidth;
        wrapper.style.overflowX = 'auto';
        // 滚动到最右边(最新数据)
        wrapper.scrollLeft = wrapper.scrollWidth;
        if (hint) hint.style.display = 'block';
    }

    // 保持canvas高度
    canvas.height = 200;
    canvas.style.height = '200px';
    if (realtimeChart) realtimeChart.resize();
}

// 滚动时更新X轴
document.addEventListener('DOMContentLoaded', function() {
    const wrapper = document.getElementById('chart-scroll-wrapper');
    if (wrapper) {
        wrapper.addEventListener('scroll', updateXAxis);
    }
});

// 加载历史数据
async function loadHistoryData(range) {
    try {
        const [tempResp, humResp, smokeResp] = await Promise.all([
            fetch(`/sensor/api/history?type=temperature&range=${range}`),
            fetch(`/sensor/api/history?type=humidity&range=${range}`),
            fetch(`/sensor/api/history?type=smoke&range=${range}`)
        ]);

        const tempData = (await tempResp.json()).data || [];
        const humData = (await humResp.json()).data || [];
        const smokeData = (await smokeResp.json()).data || [];

        if (!realtimeChart) return;

        // 用温度时间戳做标签
        const labels = tempData.map(d => {
            const parts = d.timestamp.split(' ');
            // 短时间段显示时钟, 长时间段显示日期+时钟
            if (range === '1h' || range === '6h') return parts[1] || parts[0];
            return parts[0].slice(5) + ' ' + (parts[1] || '').slice(0, 5);
        });

        realtimeChart.data.labels = labels;
        realtimeChart.data.datasets[0].data = tempData.map(d => d.value);
        realtimeChart.data.datasets[1].data = humData.map(d => d.value);
        realtimeChart.data.datasets[2].data = smokeData.map(d => d.value);
        realtimeChart.update('none');

        adjustChartWidth(labels.length);
        updateYAxis();
        updateXAxis();
    } catch (e) {
        console.error('Failed to load history data:', e);
    }
}

// 实时追加数据点到图表
function appendRealtimePoint(type, value, timestamp) {
    if (!realtimeChart) return;

    const time = timestamp.split(' ')[1] || timestamp;
    const labels = realtimeChart.data.labels;

    // 只在时间标签变化时添加新标签(避免同秒重复)
    if (labels.length === 0 || labels[labels.length - 1] !== time) {
        labels.push(time);
        if (labels.length > maxRealtimePoints) labels.shift();
    }

    const datasetIndex = {temperature: 0, humidity: 1, smoke: 2}[type];
    if (datasetIndex === undefined) return;

    const dataset = realtimeChart.data.datasets[datasetIndex];
    dataset.data.push(value);
    if (dataset.data.length > maxRealtimePoints) dataset.data.shift();

    // 保持所有数据集长度一致
    const maxLen = Math.max(...realtimeChart.data.datasets.map(d => d.data.length));
    realtimeChart.data.datasets.forEach(ds => {
        while (ds.data.length < maxLen) ds.data.unshift(null);
        while (ds.data.length > maxRealtimePoints) ds.data.shift();
    });
    while (labels.length > maxRealtimePoints) labels.shift();

    realtimeChart.update('none');
    updateYAxis();
    updateXAxis();
}

function getStatusBadge(type, value) {
    const t = thresholds[type];
    if (!t) return {text: '正常', class: 'bg-success'};

    if (type === 'smoke') {
        if (value >= t.high) return {text: '危险', class: 'bg-danger alert-pulse'};
        return {text: '正常', class: 'bg-success'};
    }

    if (value >= t.high) return {text: '偏高', class: 'bg-danger alert-pulse'};
    if (value <= t.low) return {text: '偏低', class: 'bg-info alert-pulse'};
    return {text: '正常', class: 'bg-success'};
}

// ---- Connection Status ----

function updateSocketIOStatus(connected) {
    const badge = document.getElementById('socketio-status-badge');
    if (!badge) return;
    if (connected) {
        badge.className = 'badge rounded-pill bg-success';
        badge.innerHTML = '<i class="bi bi-hdd-network"></i> SocketIO: 已连接';
    } else {
        badge.className = 'badge rounded-pill bg-warning text-dark';
        badge.innerHTML = '<i class="bi bi-hdd-network"></i> SocketIO: 重连中...';
    }
}

async function checkMqttStatus() {
    const badge = document.getElementById('mqtt-status-badge');
    if (!badge) return;
    try {
        const resp = await fetch('/sensor/api/connection');
        const data = await resp.json();
        if (data.mqtt.connected) {
            badge.className = 'badge rounded-pill bg-success';
            badge.innerHTML = '<i class="bi bi-broadcast"></i> MQTT: 已连接';
        } else {
            badge.className = 'badge rounded-pill bg-danger';
            badge.innerHTML = '<i class="bi bi-broadcast"></i> MQTT: 未连接';
        }
    } catch (e) {
        badge.className = 'badge rounded-pill bg-secondary';
        badge.innerHTML = '<i class="bi bi-broadcast"></i> MQTT: 未知';
    }
}

checkMqttStatus();
setInterval(checkMqttStatus, 10000);

// ---- SocketIO Events ----

socket.on('connect', function() {
    updateSocketIOStatus(true);
    console.log('[SocketIO] Connected');
});

socket.on('disconnect', function() {
    updateSocketIOStatus(false);
    console.log('[SocketIO] Disconnected');
});

socket.on('connect_error', function(err) {
    updateSocketIOStatus(false);
    console.warn('[SocketIO] Connection error:', err.message);
});

// Handle real-time sensor updates
socket.on('sensor_update', function(data) {
    const config = sensorConfig[data.type];
    if (!config) return;

    // 更新数值卡片
    const valueElem = document.getElementById(config.elem);
    if (valueElem) valueElem.textContent = data.value.toFixed(1) + ' ' + config.unit;

    const timeElem = document.getElementById(config.timeElem);
    if (timeElem) timeElem.textContent = data.timestamp;

    const status = getStatusBadge(data.type, data.value);
    const statusElem = document.getElementById(config.statusElem);
    if (statusElem) {
        statusElem.textContent = status.text;
        statusElem.className = 'badge ' + status.class;
    }

    // 只在 1h 模式下实时追加图表数据
    if (currentRange === '1h') {
        appendRealtimePoint(data.type, data.value, data.timestamp);
    }
});

// Load initial data
async function loadInitialData() {
    try {
        const resp = await fetch('/sensor/api/latest');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        for (const [type, info] of Object.entries(data)) {
            if (info.value !== null) {
                const config = sensorConfig[type];
                if (!config) continue;
                const elem = document.getElementById(config.elem);
                if (elem) elem.textContent = info.value.toFixed(1) + ' ' + config.unit;
                const timeElem = document.getElementById(config.timeElem);
                if (timeElem) timeElem.textContent = info.timestamp;
                const status = getStatusBadge(type, info.value);
                const statusElem = document.getElementById(config.statusElem);
                if (statusElem) {
                    statusElem.textContent = status.text;
                    statusElem.className = 'badge ' + status.class;
                }
            }
        }
    } catch (e) {
        console.error('Failed to load initial data:', e);
    }
}

// Range button handlers
document.querySelectorAll('[data-range]').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentRange = this.getAttribute('data-range');

        // 切换任何范围都从API加载数据, 1h也一样(保证不丢失历史)
        loadHistoryData(currentRange);
    });
});

// Initialize
initChart();
loadHistoryData('1h');
loadInitialData();
