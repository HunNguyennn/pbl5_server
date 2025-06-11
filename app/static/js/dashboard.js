// static/js/dashboard.js
// Quản lý realtime dashboard cho Thùng Rác Thông Minh

// Chart instances
let pieChart, specificWasteChart, dailyStatsChart;
let currentPeriod = 'day';
let currentTimeView = 'day';

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
    if (data.type === 'waste_detection') {
        showWsNotification(
            `Nhận diện mới: ${data.waste_type} (${data.specific_waste}), độ tin cậy: ${Math.round(data.confidence * 100)}%`
        );
    }
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
        // const res = await fetch('/api/stats');
        const res = await fetch(`/api/stats?period=${currentPeriod}`);
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
        // drawDaily(stats.daily_stats);
        drawDaily(stats.time_stats);
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
                        <img src="/static/images/default_detection.jpg" onerror="this.src='/static/images/default_detection.jpg'" data-src="${detection.result_image}" class="recent-detection-img img-fluid" style="width: 100%; height: auto; object-fit: contain; cursor:pointer;" />
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
    const total = organic + inorganic;
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
            tooltip: {
                callbacks: {
                    label: function (context) {
                        const value = context.raw;
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${context.label}: ${value} (${percentage}%)`;
                    }
                }
            },
            legend: {
                position: 'bottom',
                labels: {
                    boxWidth: 15,
                    padding: 15,
                    font: {
                        size: 12
                    }
                }
            }
        }
    };

    if (pieChart) {
        pieChart.data = data;
        pieChart.options = options;
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

    // Nếu không có dữ liệu
    if (!data || Object.keys(data).length === 0) {
        if (dailyStatsChart) {
            dailyStatsChart.destroy();
            dailyStatsChart = null;
        }
        return;
    }

    const dates = Object.keys(data).sort();
    const orgArr = dates.map(d => data[d].huu_co || 0);
    const inoArr = dates.map(d => data[d].vo_co || 0);

    // Format lại nhãn thời gian theo view type
    const formattedLabels = dates.map(d => {
        if (currentTimeView === 'month') {
            // Nhóm theo tuần trong tháng
            const date = new Date(d);
            const weekNumber = Math.ceil((date.getDate()) / 7);
            return `Tuần ${weekNumber}`;
        } else if (currentTimeView === 'week') {
            // Hiển thị tên thứ trong tuần
            const date = new Date(d);
            return date.toLocaleDateString('vi-VN', {
                weekday: 'long',
                day: '2-digit',
                month: '2-digit'
            });
        } else {
            // Hiển thị ngày/tháng
            const date = new Date(d);
            return date.toLocaleDateString('vi-VN', {
                day: '2-digit',
                month: '2-digit'
            });
        }
    });

    const chartData = {
        labels: formattedLabels,
        datasets: [
            {
                label: 'Hữu cơ',
                data: orgArr,
                backgroundColor: 'rgba(40, 167, 69, 0.8)',
                borderColor: 'rgba(40, 167, 69, 1)',
                borderWidth: 1,
                borderRadius: 4,
                fill: true
            },
            {
                label: 'Vô cơ',
                data: inoArr,
                backgroundColor: 'rgba(220, 53, 69, 0.8)',
                borderColor: 'rgba(220, 53, 69, 1)',
                borderWidth: 1,
                borderRadius: 4,
                fill: true
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                stacked: true, // Luôn stacked vì giờ dùng bar chart
                grid: {
                    display: false,
                    drawBorder: false
                },
                ticks: {
                    font: {
                        size: 11
                    },
                    maxRotation: 45,
                    minRotation: 45
                },
                // // Thêm cấu hình để điều chỉnh độ rộng cột
                // afterFit: function (scale) {
                //     // Điều chỉnh khoảng cách giữa các cột
                //     if (Object.keys(data).length <= 7) {
                //         scale.paddingOuter = 0.5; // Tăng padding bên ngoài
                //         scale.paddingInner = 0.3; // Tăng khoảng cách giữa các cột
                //     } else {
                //         scale.paddingOuter = 0.2;
                //         scale.paddingInner = 0.1;
                //     }
                // }
            },
            y: {
                stacked: true, // Luôn stacked vì giờ dùng bar chart
                beginAtZero: true,
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    precision: 0,
                    font: {
                        size: 11
                    },
                    // // Đảm bảo đủ steps trên trục y
                    // callback: function (value) {
                    //     if (Math.floor(value) === value) {
                    //         return value;
                    //     }
                    // }
                }
            }
        },
        plugins: {
            legend: {
                position: 'top',
                align: 'end',
                labels: {
                    boxWidth: 12,
                    padding: 15,
                    font: {
                        size: 12
                    }
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                titleColor: '#000',
                bodyColor: '#000',
                borderColor: 'rgba(0, 0, 0, 0.1)',
                borderWidth: 1,
                padding: 10,
                boxPadding: 4,
                callbacks: {
                    label: function (context) {
                        return `${context.dataset.label}: ${context.parsed.y} lượt`;
                    }
                }
            }
        },
        // Thêm cấu hình cho bars
        barPercentage: 0.4, // Điều chỉnh độ rộng của cột
        categoryPercentage: 0.7, // Điều chỉnh khoảng cách giữa nhóm cột
        animation: {
            duration: 750,
            easing: 'easeInOutQuart'
        },
        animation: {
            duration: 750,
            easing: 'easeInOutQuart'
        },
        interaction: {
            intersect: false,
            mode: 'index'
        },
        layout: {
            padding: {
                left: 10,
                right: 10
            }
        }
    };

    if (dailyStatsChart) {
        dailyStatsChart.destroy();
    }

    // Luôn dùng bar chart
    dailyStatsChart = new Chart(ctx, {
        type: 'bar',
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

function showWsNotification(message) {
    const toast = document.getElementById('ws-notification');
    const body = document.getElementById('ws-notification-body');
    if (body) body.innerText = message || 'Đã nhận dữ liệu mới từ Raspberry Pi!';
    if (toast) {
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 4000);
    }
}

function hideWsNotification() {
    const toast = document.getElementById('ws-notification');
    if (toast) toast.style.display = 'none';
}

// Hiển thị tên loại rác cụ thể tiếng Việt nếu là 1 trong 10 loại mới
function getWasteVNName(className) {
    switch (className) {
        case 'Battery': return 'Pin';
        case 'Cigarrette': return 'Đầu lọc thuốc lá';
        case 'EggShell': return 'Vỏ trứng';
        case 'OrangePeel': return 'Vỏ cam/quýt';
        case 'Paper': return 'Giấy';
        case 'PaperCup': return 'Cốc giấy';
        case 'BananaPeel': return 'Vỏ chuối';
        case 'Cans': return 'Lon kim loại';
        case 'PlasticBottle': return 'Chai nhựa';
        case 'bone': return 'Xương động vật';
        default: return className;
    }
}

// Trong các chỗ hiển thị specific_waste, có thể dùng getWasteVNName(r.specific_waste) nếu muốn hiển thị tiếng Việt.

// Thêm hàm showDetectionDetails vào cuối file
async function showDetectionDetails(id) {
    try {
        const response = await fetch(`/api/detections/` + id);
        const data = await response.json();
        console.log('API /api/detections/' + id + ' response:', data); // DEBUG
        if (!data.success || !data.detection) {
            alert('Không thể tải chi tiết phát hiện. Định dạng dữ liệu không hợp lệ.');
            return;
        }
        const detection = data.detection;
        console.log('Detection object:', detection); // DEBUG
        const modalOrigImg = document.getElementById('modal-original-image');
        const modalResultImg = document.getElementById('modal-result-image');
        modalOrigImg.src = detection.orig_image || '/static/images/default_detection.jpg';
        modalResultImg.src = detection.result_image || '/static/images/default_detection.jpg';
        document.getElementById('modal-waste-name-vn').textContent = getWasteVNName(detection.specific_waste);
        if (document.getElementById('modal-waste-name-en')) {
            document.getElementById('modal-waste-name-en').textContent = detection.specific_waste;
        }
        document.getElementById('modal-waste-type').textContent = detection.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ';
        document.getElementById('modal-confidence').textContent = (detection.confidence * 100).toFixed(1) + '%';
        document.getElementById('modal-timestamp').textContent = new Date(detection.timestamp)
            .toLocaleString('vi-VN', {
                timeZone: 'Asia/Ho_Chi_Minh',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        document.getElementById('modal-processing-time').textContent = detection.processing_time.toFixed(3);
        document.getElementById('modal-object-count').textContent = detection.object_count;
        // Hiển thị modal (luôn khởi tạo lại instance)
        const modalEl = document.getElementById('detectionModal');
        if (window.bootstrap && bootstrap.Modal) {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        } else {
            modalEl.style.display = 'block';
        }
    } catch (error) {
        alert('Không thể tải chi tiết phát hiện. Vui lòng thử lại sau.');
    }
}

// Thêm event listeners cho controls
document.getElementById('overview-period').addEventListener('change', function (e) {
    currentPeriod = e.target.value;
    loadStatistics();
});

document.getElementById('time-view').addEventListener('change', function (e) {
    currentTimeView = e.target.value;
    loadStatistics();
});