document.addEventListener('DOMContentLoaded', function () {
    // Elements for camera tab
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const startCameraBtn = document.getElementById('start-camera');
    const stopCameraBtn = document.getElementById('stop-camera');
    const captureBtn = document.getElementById('capture');
    const analyzeBtn = document.getElementById('analyze');
    const cameraStatus = document.getElementById('camera-status');
    const resultSection = document.getElementById('result-section');
    const capturedImage = document.getElementById('captured-image');
    const resultImage = document.getElementById('result-image');
    const resultContent = document.getElementById('result-content');
    const loadingResult = document.getElementById('loading-result');

    // Elements for upload tab
    const uploadContainer = document.getElementById('upload-container');
    const fileInput = document.getElementById('file-input');
    const browseButton = document.getElementById('browse-button');
    const uploadedImage = document.getElementById('uploaded-image');
    const uploadResultImage = document.getElementById('upload-result-image');
    const uploadResultContent = document.getElementById('upload-result-content');
    const uploadLoadingResult = document.getElementById('upload-loading-result');
    const analyzeUploadBtn = document.getElementById('analyze-upload');
    const uploadResultSection = document.getElementById('upload-result-section');

    let stream = null;
    let capturedImageData = null;
    let uploadedImageData = null;

    // Camera control functions
    startCameraBtn.addEventListener('click', async function () {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment'
                }
            });
            video.srcObject = stream;

            startCameraBtn.disabled = true;
            stopCameraBtn.disabled = false;
            captureBtn.disabled = false;
            analyzeBtn.disabled = true;

            cameraStatus.textContent = 'Camera đang hoạt động';
            cameraStatus.style.backgroundColor = 'rgba(40, 167, 69, 0.7)';
        } catch (err) {
            console.error('Không thể truy cập camera: ', err);
            alert('Không thể truy cập camera. Hãy kiểm tra quyền truy cập camera của trình duyệt.');
            cameraStatus.textContent = 'Lỗi truy cập camera';
            cameraStatus.style.backgroundColor = 'rgba(220, 53, 69, 0.7)';
        }
    });

    stopCameraBtn.addEventListener('click', function () {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            video.srcObject = null;
            stream = null;

            startCameraBtn.disabled = false;
            stopCameraBtn.disabled = true;
            captureBtn.disabled = true;

            cameraStatus.textContent = 'Camera đang tắt';
            cameraStatus.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
        }
    });

    captureBtn.addEventListener('click', function () {
        if (stream) {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);

            capturedImageData = canvas.toDataURL('image/jpeg');
            capturedImage.src = capturedImageData;

            resultSection.style.display = 'flex';
            analyzeBtn.disabled = false;

            // Scroll to result section
            resultSection.scrollIntoView({ behavior: 'smooth' });
        }
    });

    analyzeBtn.addEventListener('click', function () {
        if (capturedImageData) {
            analyzeImage(capturedImageData, resultImage, resultContent, loadingResult);
        }
    });

    // File upload functions
    browseButton.addEventListener('click', function () {
        fileInput.click();
    });

    uploadContainer.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadContainer.classList.add('border-primary');
    });

    uploadContainer.addEventListener('dragleave', function () {
        uploadContainer.classList.remove('border-primary');
    });

    uploadContainer.addEventListener('drop', function (e) {
        e.preventDefault();
        uploadContainer.classList.remove('border-primary');

        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', function () {
        if (fileInput.files.length) {
            handleFile(fileInput.files[0]);
        }
    });

    analyzeUploadBtn.addEventListener('click', function () {
        if (uploadedImageData) {
            analyzeImage(uploadedImageData, uploadResultImage, uploadResultContent, uploadLoadingResult);
        }
    });

    function handleFile(file) {
        if (file.type.match('image.*')) {
            const reader = new FileReader();

            reader.onload = function (e) {
                uploadedImageData = e.target.result;
                uploadedImage.src = uploadedImageData;
                uploadResultSection.style.display = 'flex';
                analyzeUploadBtn.disabled = false;

                // Scroll to result section
                uploadResultSection.scrollIntoView({ behavior: 'smooth' });
            };

            reader.readAsDataURL(file);
        } else {
            alert('Vui lòng chọn file ảnh hợp lệ.');
        }
    }

    // Function to analyze image using API
    function analyzeImage(imageData, resultImgElement, resultContentElement, loadingElement) {
        loadingElement.classList.remove('d-none');
        resultContentElement.innerHTML = '';

        fetch('/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageData
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Lỗi khi phân tích ảnh');
                }
                return response.json();
            })
            .then(data => {
                loadingElement.classList.add('d-none');

                if (data.error) {
                    resultContentElement.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        ${data.error}
                    </div>
                `;
                    return;
                }

                // Display result image
                resultImgElement.src = data.image;

                // Kiểm tra dữ liệu trả về từ API và chuyển đổi waste_type
                const wasteType = data.classification_result ? data.classification_result.waste_type : (data.waste_type || 'unknown');
                const confidence = data.classification_result ? data.classification_result.confidence : (data.confidence || 0);

                // Chuyển đổi từ huu_co/vo_co thành organic/inorganic để hiển thị đúng
                const wasteTypeForDisplay = wasteType === 'huu_co' ? 'organic' : (wasteType === 'vo_co' ? 'inorganic' : wasteType);
                const badgeColor = wasteTypeForDisplay === 'organic' ? 'success' : 'primary';
                const wasteTypeText = wasteTypeForDisplay === 'organic' ? 'Hữu cơ' : 'Vô cơ';

                let detailsHTML = `
                <div class="alert alert-${badgeColor} mb-3">
                    <h5 class="mb-1"><i class="bi bi-tag-fill me-2"></i>Loại rác: <span class="badge bg-${badgeColor}">${wasteTypeText}</span></h5>
                    <p class="mb-0">Độ tin cậy: ${(confidence * 100).toFixed(2)}%</p>
                </div>
            `;

                // Add detailed detections if available
                if (data.detections && data.detections.length > 0) {
                    detailsHTML += `
                    <h6 class="mt-3 mb-2"><i class="bi bi-list-ul me-2"></i>Chi tiết phát hiện:</h6>
                    <ul class="list-group">
                `;

                    data.detections.forEach(detection => {
                        // Chuyển đổi từ huu_co/vo_co thành organic/inorganic
                        const detWasteType = detection.waste_type === 'huu_co' ? 'organic' : (detection.waste_type === 'vo_co' ? 'inorganic' : detection.waste_type);
                        const detBadgeColor = detWasteType === 'organic' ? 'success' : 'primary';
                        const detWasteTypeText = detWasteType === 'organic' ? 'Hữu cơ' : 'Vô cơ';

                        detailsHTML += `
                        <li class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <span>${detection.class}</span>
                                <div>
                                    <span class="badge bg-${detBadgeColor} me-1">${detWasteTypeText}</span>
                                    <span class="badge bg-dark">${(detection.confidence * 100).toFixed(2)}%</span>
                                </div>
                            </div>
                        </li>
                    `;
                    });

                    detailsHTML += `</ul>`;
                }

                resultContentElement.innerHTML = detailsHTML;
            })
            .catch(error => {
                loadingElement.classList.add('d-none');
                resultContentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
                console.error('Error:', error);
            });
    }

    // Tab switching event to handle camera stop
    const analysisTabs = document.getElementById('analysisTabs');
    analysisTabs.addEventListener('shown.bs.tab', function (e) {
        if (e.target.id !== 'camera-tab' && stream) {
            // If switching away from camera tab, stop the camera
            stopCameraBtn.click();
        }
    });
});
