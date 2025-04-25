// static/js/dashboard.js
// Quản lý realtime dashboard cho Thùng Rác Thông Minh

// Chart instances
let pieChart, specificWasteChart, dailyStatsChart;

// Mở kết nối WebSocket với endpoint /dashboard/ws
const dashboardWs = new WebSocket(`ws://${window.location.host}/dashboard/ws`);

dashboardWs.onopen = () => {
    console.log('WS /dashboard/ws connected');
};

dashboardWs.onmessage = event => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};

dashboardWs.onclose = () => console.log('WS /dashboard/ws closed');

dashboardWs.onerror = err => console.error('WS error:', err);

// Cập nhật UI khi nhận dữ liệu mới
function updateDashboard(data) {
    // Cập nhật thời gian
    document.getElementById('last-update-time').innerText = new Date().toLocaleTimeString();

    // Cập nhật khoảng cách cảm biến
    if (data.sensor && data.sensor.distance !== undefined) {
        document.getElementById('current-distance').innerText = data.sensor.distance.toFixed(1);
    }

    // Cập nhật feed phân loại mới nhất
    if (data.recent_records && data.recent_records.length > 0) {
        const noDataEl = document.getElementById('no-data-message');
        if (noDataEl) noDataEl.remove();

        const ul = document.getElementById('recent-records');
        const r = data.recent_records[0];
        const time = new Date(r.timestamp).toLocaleTimeString();

        const li = document.createElement('li');
        li.className = `list-group-item ${r.waste_type === 'huu_co' ? 'waste-organic' : 'waste-inorganic'}`;
        li.innerHTML = `
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <strong>${r.specific_waste}</strong>
          <span class="badge ms-2 ${r.waste_type === 'huu_co' ? 'bg-success' : 'bg-danger'}">
            ${r.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ'}
          </span>
        </div>
        <small>${time}</small>
      </div>
      <div>Độ tin cậy: ${(r.confidence * 100).toFixed(1)}%</div>
    `;

        ul.prepend(li);
        if (ul.children.length > 10) ul.removeChild(ul.lastChild);
    }

    // Nếu cần reload thống kê
    if (data.stats_updated) loadStatistics();
}

// Fetch và cập nhật các biểu đồ thống kê toàn cục
async function loadStatistics() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();

        // Cập nhật số liệu tổng quan
        const org = stats.waste_counts.huu_co || 0;
        const ino = stats.waste_counts.vo_co || 0;
        document.getElementById('organic-count').innerText = org;
        document.getElementById('inorganic-count').innerText = ino;
        document.getElementById('total-count').innerText = org + ino;

        // Vẽ/Update biểu đồ
        drawPie(org, ino);
        drawSpecific(stats.specific_waste);
        drawDaily(stats.daily_stats);
    } catch (e) {
        console.error('Lỗi loadStatistics:', e);
    }
}

function drawPie(organic, inorganic) {
    const ctx = document.getElementById('waste-pie-chart').getContext('2d');
    if (pieChart) {
        pieChart.data.datasets[0].data = [organic, inorganic];
        pieChart.update();
        return;
    }
    pieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Hữu cơ', 'Vô cơ'],
            datasets: [{ data: [organic, inorganic] }]
        }
    });
}

function drawSpecific(data) {
    const ctx = document.getElementById('specific-waste-chart').getContext('2d');
    const labels = Object.keys(data);
    const vals = Object.values(data);
    if (specificWasteChart) {
        specificWasteChart.data.labels = labels;
        specificWasteChart.data.datasets[0].data = vals;
        specificWasteChart.update();
        return;
    }
    specificWasteChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Số lượng', data: vals }]
        }
    });
}

function drawDaily(data) {
    const ctx = document.getElementById('daily-stats-chart').getContext('2d');
    const dates = Object.keys(data).sort();
    const orgArr = dates.map(d => data[d].huu_co || 0);
    const inoArr = dates.map(d => data[d].vo_co || 0);
    if (dailyStatsChart) {
        dailyStatsChart.data.labels = dates;
        dailyStatsChart.data.datasets[0].data = orgArr;
        dailyStatsChart.data.datasets[1].data = inoArr;
        dailyStatsChart.update();
        return;
    }
    dailyStatsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                { label: 'Hữu cơ', data: orgArr, fill: true },
                { label: 'Vô cơ', data: inoArr, fill: true }
            ]
        }
    });
}

// Xử lý nút reset
const btnReset = document.getElementById('reset-stats');
if (btnReset) {
    btnReset.addEventListener('click', async () => {
        if (!confirm('Bạn có chắc chắn reset thống kê?')) return;
        try {
            const r = await fetch('/api/stats/reset', { method: 'POST' });
            if (r.ok) {
                alert('Đã reset');
                loadStatistics();
            } else {
                alert('Reset thất bại');
            }
        } catch (err) {
            console.error('Reset error:', err);
            alert('Có lỗi xảy ra khi reset');
        }
    });
}

// Khởi tạo khi tải trang
window.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    fetch('/api/realtime')
        .then(r => r.json())
        .then(d => updateDashboard({ ...d, stats_updated: false }));
});
