// Biến để lưu trữ các biểu đồ
let pieChart, specificWasteChart, dailyStatsChart;

// WebSocket để nhận dữ liệu thời gian thực
const dashboardWs = new WebSocket(`ws://${window.location.host}/dashboard/ws`);

dashboardWs.onopen = function () {
    console.log("Dashboard WebSocket connected");
    // Gửi ping mỗi 30 giây để giữ kết nối
    setInterval(() => {
        if (dashboardWs.readyState === WebSocket.OPEN) {
            dashboardWs.send("ping");
        }
    }, 30000);
};

dashboardWs.onmessage = function (event) {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};

// Hàm cập nhật dashboard khi có dữ liệu mới
function updateDashboard(data) {
    // Cập nhật thời gian
    document.getElementById('last-update-time').innerText = new Date().toLocaleTimeString();

    // Cập nhật khoảng cách nếu có
    if (data.sensor && data.sensor.distance) {
        document.getElementById('current-distance').innerText = data.sensor.distance.toFixed(1);
    }

    // Cập nhật danh sách phân loại gần đây
    if (data.recent_records && data.recent_records.length > 0) {
        document.getElementById('no-data-message').style.display = 'none';

        const recordsList = document.getElementById('recent-records');
        // Thêm bản ghi mới vào đầu danh sách
        const record = data.recent_records[0]; // Chỉ lấy bản ghi mới nhất

        const li = document.createElement('li');
        li.className = `list-group-item ${record.waste_type === 'huu_co' ? 'waste-organic' : 'waste-inorganic'}`;

        const timestamp = new Date(record.timestamp).toLocaleTimeString();
        li.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${record.specific_waste}</strong>
                    <span class="badge ${record.waste_type === 'huu_co' ? 'bg-success' : 'bg-danger'} ms-2">
                        ${record.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ'}
                    </span>
                </div>
                <small>${timestamp}</small>
            </div>
            <div>Độ tin cậy: ${(record.confidence * 100).toFixed(1)}%</div>
        `;

        recordsList.insertBefore(li, recordsList.firstChild);

        // Giới hạn số lượng hiển thị
        if (recordsList.children.length > 10) {
            recordsList.removeChild(recordsList.lastChild);
        }
    }

    // Tải lại dữ liệu thống kê nếu cần
    if (data.stats_updated) {
        loadStatistics();
    }
}

// Hàm tải dữ liệu thống kê từ API
async function loadStatistics() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        // Cập nhật số liệu tổng quan
        const organicCount = stats.waste_counts.huu_co || 0;
        const inorganicCount = stats.waste_counts.vo_co || 0;
        const totalCount = organicCount + inorganicCount;

        document.getElementById('organic-count').innerText = organicCount;
        document.getElementById('inorganic-count').innerText = inorganicCount;
        document.getElementById('total-count').innerText = totalCount;

        // Cập nhật biểu đồ tròn
        updatePieChart(organicCount, inorganicCount);

        // Cập nhật biểu đồ loại rác cụ thể
        updateSpecificWasteChart(stats.specific_waste);

        // Cập nhật biểu đồ theo ngày
        updateDailyStatsChart(stats.daily_stats);

    } catch (error) {
        console.error("Lỗi khi tải dữ liệu thống kê:", error);
    }
}

// Hàm cập nhật biểu đồ tròn
function updatePieChart(organicCount, inorganicCount) {
    const ctx = document.getElementById('waste-pie-chart').getContext('2d');

    if (pieChart) {
        pieChart.data.datasets[0].data = [organicCount, inorganicCount];
        pieChart.update();
    } else {
        pieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Hữu cơ', 'Vô cơ'],
                datasets: [{
                    data: [organicCount, inorganicCount],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// Hàm cập nhật biểu đồ loại rác cụ thể
function updateSpecificWasteChart(specificWasteData) {
    const ctx = document.getElementById('specific-waste-chart').getContext('2d');

    const labels = Object.keys(specificWasteData);
    const data = Object.values(specificWasteData);

    // Màu cho từng loại rác cụ thể
    const colors = {
        'bananapeel': '#66bb6a',   // Xanh lá đậm
        'eggsell': '#a5d6a7',      // Xanh lá nhạt
        'bottlescans': '#f44336',  // Đỏ
        'paper': '#ef9a9a',        // Hồng
        'plasticbag': '#e57373'    // Đỏ nhạt
    };

    const backgroundColor = labels.map(label => colors[label] || '#777777');

    if (specificWasteChart) {
        specificWasteChart.data.labels = labels;
        specificWasteChart.data.datasets[0].data = data;
        specificWasteChart.data.datasets[0].backgroundColor = backgroundColor;
        specificWasteChart.update();
    } else {
        specificWasteChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Số lượng',
                    data: data,
                    backgroundColor: backgroundColor
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
}

// Hàm cập nhật biểu đồ thống kê theo ngày
function updateDailyStatsChart(dailyStats) {
    const ctx = document.getElementById('daily-stats-chart').getContext('2d');

    // Chuyển đổi dữ liệu
    const dates = Object.keys(dailyStats).sort();
    const organicData = dates.map(date => dailyStats[date].huu_co || 0);
    const inorganicData = dates.map(date => dailyStats[date].vo_co || 0);

    if (dailyStatsChart) {
        dailyStatsChart.data.labels = dates;
        dailyStatsChart.data.datasets[0].data = organicData;
        dailyStatsChart.data.datasets[1].data = inorganicData;
        dailyStatsChart.update();
    } else {
        dailyStatsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Hữu cơ',
                        data: organicData,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.2)',
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Vô cơ',
                        data: inorganicData,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Ngày'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Số lượng'
                        },
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
}

// Xử lý nút reset
document.getElementById('reset-stats').addEventListener('click', async function () {
    if (confirm('Bạn có chắc chắn muốn xóa tất cả dữ liệu thống kê?')) {
        try {
            const response = await fetch('/api/stats/reset', {
                method: 'POST'
            });

            if (response.ok) {
                alert('Đã reset thống kê thành công!');
                loadStatistics(); // Tải lại thống kê
            } else {
                alert('Không thể reset thống kê!');
            }
        } catch (error) {
            console.error("Lỗi khi reset thống kê:", error);
            alert('Đã xảy ra lỗi khi reset thống kê!');
        }
    }
});

// Tải dữ liệu ban đầu
async function loadInitialData() {
    // Tải dữ liệu thống kê
    await loadStatistics();

    // Tải dữ liệu thời gian thực
    try {
        const response = await fetch('/api/realtime');
        const data = await response.json();

        // Cập nhật khoảng cách cảm biến
        if (data.sensor && data.sensor.distance) {
            document.getElementById('current-distance').innerText = data.sensor.distance.toFixed(1);
        }

        // Cập nhật danh sách phân loại gần đây
        if (data.recent_records && data.recent_records.length > 0) {
            document.getElementById('no-data-message').style.display = 'none';

            const recordsList = document.getElementById('recent-records');
            recordsList.innerHTML = ''; // Xóa dữ liệu cũ

            data.recent_records.forEach(record => {
                const li = document.createElement('li');
                li.className = `list-group-item ${record.waste_type === 'huu_co' ? 'waste-organic' : 'waste-inorganic'}`;

                const timestamp = new Date(record.timestamp).toLocaleTimeString();
                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${record.specific_waste}</strong>
                            <span class="badge ${record.waste_type === 'huu_co' ? 'bg-success' : 'bg-danger'} ms-2">
                                ${record.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ'}
                            </span>
                        </div>
                        <small>${timestamp}</small>
                    </div>
                    <div>Độ tin cậy: ${(record.confidence * 100).toFixed(1)}%</div>
                `;

                recordsList.appendChild(li);
            });
        }

    } catch (error) {
        console.error("Lỗi khi tải dữ liệu thời gian thực:", error);
    }

    // Cập nhật thời gian
    document.getElementById('last-update-time').innerText = new Date().toLocaleTimeString();
}

// Tải dữ liệu khi trang được tải
document.addEventListener('DOMContentLoaded', loadInitialData);

document.getElementById("start-camera").addEventListener("click", async () => {
    const video = document.getElementById("video");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (error) {
        console.error("Lỗi khi truy cập webcam:", error);
        alert("Không thể truy cập camera. Vui lòng kiểm tra quyền hoặc kết nối.");
    }
});
