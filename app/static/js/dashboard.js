// static/js/dashboard.js
// Quản lý realtime dashboard cho Thùng Rác Thông Minh

// Chart instances
let pieChart, specificWasteChart, dailyStatsChart;

// Mở kết nối WebSocket với endpoint /dashboard/ws
const dashboardWs = new WebSocket(`ws://${window.location.host}/dashboard/ws`);

dashboardWs.onopen = () => {
    console.log('WS /dashboard/ws connected');
    // Gửi ping mỗi 30 giây để giữ kết nối
    setInterval(() => {
        if (dashboardWs.readyState === WebSocket.OPEN) {
            dashboardWs.send('ping');
        }
    }, 30000);
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
    document.getElementById('last-update-time').innerText = new Date().toLocaleString('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });

    // Cập nhật khoảng cách hiện tại (nếu có)
    if (data.sensor && data.sensor.distance) {
        document.getElementById('current-distance').innerText = data.sensor.distance;
    }

    // Thêm bản ghi mới vào feed
    if (data.recent_records && data.recent_records.length > 0) {
        const recentRecords = document.getElementById('recent-records');
        const noDataMessage = document.getElementById('no-data-message');

        // Ẩn thông báo không có dữ liệu
        noDataMessage.style.display = 'none';

        data.recent_records.forEach(r => {
            const li = document.createElement('li');
            const time = new Date(r.timestamp).toLocaleString('vi-VN', {
                timeZone: 'Asia/Ho_Chi_Minh',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });

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
                <div>
                    Độ tin cậy: <span class="fw-bold">${(r.confidence * 100).toFixed(1)}%</span>
                </div>
            `;

            // Thêm bản ghi mới vào đầu danh sách
            recentRecords.insertBefore(li, recentRecords.firstChild);

            // Giới hạn số lượng bản ghi hiển thị (chỉ hiển thị 5 bản ghi gần nhất)
            if (recentRecords.children.length > 5) {
                recentRecords.removeChild(recentRecords.lastChild);
            }
        });
    }

    // Cập nhật số liệu thống kê nếu có thay đổi
    if (data.stats_updated) {
        loadStatistics();
        loadRecentDetections();
    }
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

// Tải danh sách phát hiện gần đây
async function loadRecentDetections() {
    try {
        const detectionsContainer = document.getElementById('recent-detections');
        const loadingElement = document.getElementById('detection-loading');
        const noDetectionsElement = document.getElementById('no-detections');

        // Hiển thị loading
        loadingElement.classList.remove('d-none');
        noDetectionsElement.classList.add('d-none');

        // Xóa các detection cũ (nếu có)
        const elementsToRemove = detectionsContainer.querySelectorAll('.col-md-3');
        elementsToRemove.forEach(el => el.remove());

        // Tải dữ liệu từ API
        const response = await fetch('/api/detections?limit=8');
        const data = await response.json();

        // Ẩn loading
        loadingElement.classList.add('d-none');

        // Kiểm tra xem có dữ liệu không
        if (!data.detections || data.detections.length === 0) {
            noDetectionsElement.classList.remove('d-none');
            return;
        }

        // Hiển thị các phát hiện
        data.detections.forEach(detection => {
            const col = document.createElement('div');
            col.className = 'col-md-3 col-sm-6 mb-4';

            const wasteTypeText = detection.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ';
            const badgeClass = detection.waste_type === 'huu_co' ? 'bg-success' : 'bg-danger';

            // Định dạng thời gian với múi giờ Việt Nam
            const formattedDate = new Date(detection.timestamp).toLocaleString('vi-VN', {
                timeZone: 'Asia/Ho_Chi_Minh',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });

            col.innerHTML = `
                <div class="card detection-tile">
                    <div class="card-body p-3">
                        <span class="badge ${badgeClass} detection-badge">${wasteTypeText}</span>
                        <a href="/dashboard/history" title="Xem chi tiết">
                            <img src="/static/images/default_detection.jpg" onerror="this.src='/static/images/default_detection.jpg'" data-src="${detection.result_image}" class="recent-detection-img img-fluid" style="width: 100%; height: auto; object-fit: contain;" />
                        </a>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong>${detection.specific_waste}</strong>
                            <small>${(detection.confidence * 100).toFixed(1)}%</small>
                        </div>
                        <small class="text-muted">${formattedDate}</small>
                    </div>
                </div>
            `;

            detectionsContainer.appendChild(col);

            // Tải ảnh sau khi đã thêm vào DOM
            setTimeout(() => {
                const img = col.querySelector('.recent-detection-img');
                if (img && img.dataset.src) {
                    img.onerror = function () {
                        this.src = '/static/images/default_detection.jpg';
                        this.onerror = null;
                    };
                    img.src = img.dataset.src;
                }
            }, 100);
        });
    } catch (error) {
        console.error('Error loading recent detections:', error);
        document.getElementById('detection-loading').classList.add('d-none');

        const noDetections = document.getElementById('no-detections');
        noDetections.classList.remove('d-none');
        noDetections.querySelector('p').textContent = 'Lỗi khi tải dữ liệu phát hiện.';
    }
}

function drawPie(organic, inorganic) {
    const ctx = document.getElementById('waste-pie-chart').getContext('2d');

    const data = {
        labels: ['Hữu cơ', 'Vô cơ'],
        datasets: [{
            data: [organic, inorganic],
            backgroundColor: ['#28a745', '#dc3545'],
            borderColor: ['#1e7e34', '#bd2130'],
            borderWidth: 1
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    boxWidth: 15,
                    padding: 15
                }
            }
        }
    };

    if (pieChart) {
        pieChart.data = data;
        pieChart.update();
        return;
    }

    pieChart = new Chart(ctx, {
        type: 'pie',
        data: data,
        options: options
    });
}

function drawSpecific(data) {
    const ctx = document.getElementById('specific-waste-chart').getContext('2d');

    // Sắp xếp dữ liệu
    const sortedLabels = Object.keys(data).sort((a, b) => data[b] - data[a]);
    const values = sortedLabels.map(label => data[label]);

    // Tạo màu ngẫu nhiên cho các loại rác
    const colors = sortedLabels.map(() => {
        const r = Math.floor(Math.random() * 200);
        const g = Math.floor(Math.random() * 200);
        const b = Math.floor(Math.random() * 200);
        return `rgba(${r}, ${g}, ${b}, 0.8)`;
    });

    const chartData = {
        labels: sortedLabels,
        datasets: [{
            label: 'Số lượng',
            data: values,
            backgroundColor: colors,
            borderColor: colors.map(c => c.replace('0.8', '1')),
            borderWidth: 1
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        },
        plugins: {
            legend: {
                display: false
            }
        }
    };

    if (specificWasteChart) {
        specificWasteChart.data = chartData;
        specificWasteChart.update();
        return;
    }

    specificWasteChart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: options
    });
}

function drawDaily(data) {
    const ctx = document.getElementById('daily-stats-chart').getContext('2d');
    const dates = Object.keys(data).sort();
    const orgArr = dates.map(d => data[d].huu_co || 0);
    const inoArr = dates.map(d => data[d].vo_co || 0);

    const chartData = {
        labels: dates,
        datasets: [
            {
                label: 'Hữu cơ',
                data: orgArr,
                fill: true,
                backgroundColor: 'rgba(40, 167, 69, 0.2)',
                borderColor: 'rgba(40, 167, 69, 1)',
                borderWidth: 2,
                tension: 0.4
            },
            {
                label: 'Vô cơ',
                data: inoArr,
                fill: true,
                backgroundColor: 'rgba(220, 53, 69, 0.2)',
                borderColor: 'rgba(220, 53, 69, 1)',
                borderWidth: 2,
                tension: 0.4
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        },
        plugins: {
            legend: {
                position: 'top',
            }
        }
    };

    if (dailyStatsChart) {
        dailyStatsChart.data = chartData;
        dailyStatsChart.update();
        return;
    }

    dailyStatsChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: options
    });
}

// Xử lý nút reset
const btnReset = document.getElementById('reset-stats');
if (btnReset) {
    btnReset.addEventListener('click', async () => {
        if (!confirm('Bạn có chắc chắn reset thống kê?')) return;
        try {
            const r = await fetch('/api/reset', { method: 'POST' });
            if (r.ok) {
                alert('Đã reset');
                loadStatistics();
                // Xóa feed phân loại mới nhất
                const ul = document.getElementById('recent-records');
                ul.innerHTML = '';
                // Hiển thị lại thông báo không có dữ liệu
                document.getElementById('no-data-message').style.display = 'block';
                // Reset phần phát hiện gần đây
                loadRecentDetections();
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
    loadRecentDetections();
    fetch('/api/realtime')
        .then(r => r.json())
        .then(d => updateDashboard({ ...d, stats_updated: false }));
});
