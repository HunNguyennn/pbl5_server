// static/js/detection_history.js
// Quản lý hiển thị lịch sử phát hiện rác

// Cấu hình
const config = {
    itemsPerPage: 12,
    apiUrl: '/api/detections',
    detailApiUrl: '/api/detections/'
};

// Biến state
let currentPage = 1;
let totalPages = 1;
let currentFilter = '';

// DOM Elements
const detectionsContainer = document.getElementById('detections-container');
const loadingIndicator = document.getElementById('loading-indicator');
const noDataMessage = document.getElementById('no-data');
const pagination = document.getElementById('pagination');
const wasteTypeFilter = document.getElementById('waste-type-filter');
const applyFilterBtn = document.getElementById('apply-filter');
const resetFilterBtn = document.getElementById('reset-filter');

// Bootstrap Modal
const detectionModal = new bootstrap.Modal(document.getElementById('detectionModal'));

// Functions
async function loadDetections() {
    showLoading();

    try {
        const offset = (currentPage - 1) * config.itemsPerPage;
        let url = `${config.apiUrl}?limit=${config.itemsPerPage}&offset=${offset}`;

        if (currentFilter) {
            url += `&waste_type=${currentFilter}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        renderDetections(data.detections);
        updatePagination(data.total);

    } catch (error) {
        console.error('Error loading detections:', error);
        showNoData('Lỗi khi tải dữ liệu: ' + error.message);
    }
}

function renderDetections(detections) {
    if (!detections || detections.length === 0) {
        showNoData();
        return;
    }

    hideLoading();
    hideNoData();

    // Clear container except loading and no-data elements
    const elementsToRemove = document.querySelectorAll('#detections-container .col-md-4');
    elementsToRemove.forEach(el => el.remove());

    // Render each detection card
    detections.forEach(detection => {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-4';

        const wasteTypeText = detection.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ';
        const wasteTypeClass = detection.waste_type === 'huu_co' ? 'waste-organic' : 'waste-inorganic';

        // Định dạng thời gian với múi giờ Việt Nam (UTC+7)
        const formattedDate = new Date(detection.timestamp)
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

        const confidencePercent = (detection.confidence * 100).toFixed(1) + '%';

        col.innerHTML = `
            <div class="card detection-card ${wasteTypeClass}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${detection.specific_waste}</span>
                    <span class="badge ${detection.waste_type === 'huu_co' ? 'bg-success' : 'bg-danger'}">${wasteTypeText}</span>
                </div>
                <div class="card-body">
                    <img src="/static/images/default_detection.jpg" data-src="${detection.result_image}" alt="${detection.specific_waste}" class="detection-image mb-3 img-fluid" 
                        data-id="${detection.id}" onclick="showDetectionDetails(${detection.id})" style="width: 100%; height: auto; object-fit: contain;">
                    <div class="d-flex justify-content-between">
                        <div>
                            <span class="stats-badge">
                                <i class="bi bi-percent"></i> ${confidencePercent}
                            </span>
                        </div>
                        <small class="text-muted">${formattedDate}</small>
                    </div>
                </div>
            </div>
        `;

        detectionsContainer.appendChild(col);

        // Tải ảnh sau khi đã thêm vào DOM
        setTimeout(() => {
            const img = col.querySelector('.detection-image');
            if (img && img.dataset.src) {
                img.onerror = function () {
                    this.src = '/static/images/default_detection.jpg';
                    this.onerror = null;
                };
                img.src = img.dataset.src;
            }
        }, 100);
    });
}

async function showDetectionDetails(id) {
    try {
        const response = await fetch(`${config.detailApiUrl}${id}`);
        const data = await response.json();

        if (!data.success || !data.detection) {
            console.error('Invalid API response format:', data);
            alert('Không thể tải chi tiết phát hiện. Định dạng dữ liệu không hợp lệ.');
            return;
        }

        const detection = data.detection;

        // Update modal content
        const modalOrigImg = document.getElementById('modal-original-image');
        const modalResultImg = document.getElementById('modal-result-image');

        modalOrigImg.onerror = function () { this.src = '/static/images/default_detection.jpg'; };
        modalResultImg.onerror = function () { this.src = '/static/images/default_detection.jpg'; };

        modalOrigImg.src = detection.orig_image || '/static/images/default_detection.jpg';
        modalResultImg.src = detection.result_image || '/static/images/default_detection.jpg';

        document.getElementById('modal-waste-name').textContent = detection.specific_waste;
        document.getElementById('modal-waste-type').textContent = detection.waste_type === 'huu_co' ? 'Hữu cơ' : 'Vô cơ';
        document.getElementById('modal-confidence').textContent = (detection.confidence * 100).toFixed(1) + '%';

        // Định dạng thời gian với múi giờ Việt Nam (UTC+7)
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

        // Show modal
        detectionModal.show();
    } catch (error) {
        console.error('Error loading detection details:', error);
        alert('Không thể tải chi tiết phát hiện. Vui lòng thử lại sau.');
    }
}

function updatePagination(totalItems) {
    totalPages = Math.ceil(totalItems / config.itemsPerPage);

    // Clear pagination
    pagination.innerHTML = '';

    // Don't show pagination if there are no items
    if (totalItems === 0) {
        pagination.parentElement.classList.add('d-none');
        return;
    } else {
        pagination.parentElement.classList.remove('d-none');
    }

    // Previous button
    const prevBtn = document.createElement('li');
    prevBtn.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevBtn.innerHTML = `<a class="page-link" href="#" aria-label="Previous" ${currentPage === 1 ? 'tabindex="-1" aria-disabled="true"' : ''}><span aria-hidden="true">&laquo;</span></a>`;
    prevBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            loadDetections();
        }
    });
    pagination.appendChild(prevBtn);

    // Page buttons
    const maxVisiblePages = 5;
    const halfVisible = Math.floor(maxVisiblePages / 2);
    let startPage = Math.max(1, currentPage - halfVisible);
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('li');
        pageBtn.className = `page-item ${i === currentPage ? 'active' : ''}`;
        pageBtn.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        pageBtn.addEventListener('click', (e) => {
            e.preventDefault();
            currentPage = i;
            loadDetections();
        });
        pagination.appendChild(pageBtn);
    }

    // Next button
    const nextBtn = document.createElement('li');
    nextBtn.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextBtn.innerHTML = `<a class="page-link" href="#" aria-label="Next" ${currentPage === totalPages ? 'tabindex="-1" aria-disabled="true"' : ''}><span aria-hidden="true">&raquo;</span></a>`;
    nextBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (currentPage < totalPages) {
            currentPage++;
            loadDetections();
        }
    });
    pagination.appendChild(nextBtn);
}

function showLoading() {
    loadingIndicator.classList.remove('d-none');
    noDataMessage.classList.add('d-none');
}

function hideLoading() {
    loadingIndicator.classList.add('d-none');
}

function showNoData(message) {
    hideLoading();
    noDataMessage.classList.remove('d-none');
    if (message) {
        noDataMessage.querySelector('p').textContent = message;
    } else {
        noDataMessage.querySelector('p').textContent = 'Không có dữ liệu phát hiện nào được tìm thấy.';
    }
}

function hideNoData() {
    noDataMessage.classList.add('d-none');
}

// Event Listeners
applyFilterBtn.addEventListener('click', () => {
    currentFilter = wasteTypeFilter.value;
    currentPage = 1; // Reset to first page
    loadDetections();
});

resetFilterBtn.addEventListener('click', () => {
    wasteTypeFilter.value = '';
    currentFilter = '';
    currentPage = 1; // Reset to first page
    loadDetections();
});

// Make the function available globally for onClick handlers
window.showDetectionDetails = showDetectionDetails;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDetections();
}); 