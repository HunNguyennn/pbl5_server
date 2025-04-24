const video = document.getElementById("video");
const btn = document.getElementById("start-camera");
let ws;

btn.addEventListener("click", async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;

        // Mở WebSocket đến /ws
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onopen = () => console.log("WebSocket /ws connected");
            ws.onclose = () => console.log("WebSocket /ws closed");
            ws.onerror = e => console.error("WS error", e);
        }

        // Gửi liên tục từng frame định kỳ
        setInterval(() => {
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext("2d").drawImage(video, 0, 0);
            const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(dataUrl);
            }
        }, 200); // 5 fps

    } catch (err) {
        console.error("Không thể truy cập camera:", err);
        alert("Hãy kiểm tra quyền camera!");
    }
});
