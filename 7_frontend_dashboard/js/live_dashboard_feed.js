/**
 * live_dashboard_feed.js
 * Handles webcam/microscope streaming with start/stop controls and FPS calculation
 */

(function() {
    console.log('[live_dashboard_feed.js] loaded');

    let videoStream = null;
    let videoElement = null;
    let isStreaming = false;
    let fpsCounter = 0;
    let lastFpsTime = Date.now();
    let animationId = null;

    function init() {
        videoElement = document.getElementById('liveVideoFeed');
        const startBtn = document.getElementById('startFeedBtn');
        const stopBtn = document.getElementById('stopFeedBtn');
        const captureBtn = document.getElementById('captureSnapshotBtn');
        const sourceToggle = document.getElementById('sourceToggle');

        if (!videoElement || !startBtn || !stopBtn) {
            console.warn('Live dashboard video elements not found');
            return;
        }

        startBtn.addEventListener('click', startFeed);
        stopBtn.addEventListener('click', stopFeed);
        if (captureBtn) {
            captureBtn.addEventListener('click', captureSnapshot);
        }
        sourceToggle.addEventListener('change', handleSourceChange);
    }

    async function startFeed() {
        if (isStreaming) return;

        try {
            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment'
                },
                audio: false
            };

            videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            videoElement.srcObject = videoStream;
            isStreaming = true;

            // Show video, hide placeholder
            videoElement.style.display = 'block';
            document.getElementById('videoPlaceholder').style.display = 'none';

            // Update button states
            document.getElementById('startFeedBtn').disabled = true;
            document.getElementById('stopFeedBtn').disabled = false;
            document.getElementById('sourceToggle').disabled = true;

            // Start FPS counter
            startFpsCounter();

            // Enable capture button if present
            const captureBtn = document.getElementById('captureSnapshotBtn');
            if (captureBtn) captureBtn.disabled = false;

        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Unable to access camera/microscope. Please check permissions.\n\n' + error.message);
        }
    }

    function stopFeed() {
        if (!isStreaming || !videoStream) return;

        isStreaming = false;

        // Stop all tracks
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
        videoElement.srcObject = null;

        // Hide video, show placeholder
        videoElement.style.display = 'none';
        document.getElementById('videoPlaceholder').style.display = 'flex';

        // Update button states
        document.getElementById('startFeedBtn').disabled = false;
        document.getElementById('stopFeedBtn').disabled = true;
        document.getElementById('sourceToggle').disabled = false;

        // Disable capture button
        const captureBtn = document.getElementById('captureSnapshotBtn');
        if (captureBtn) captureBtn.disabled = true;

        // Stop FPS counter
        stopFpsCounter();
        document.getElementById('fpsValue').textContent = '0 FPS';
    }

    /**
     * Capture current video frame and upload as PNG to the backend.
     * Posts to '/api/upload_snapshot' as multipart/form-data with field 'file'.
     */
    function captureSnapshot() {
        if (!isStreaming || !videoElement) return showSnapshotToast('No active video to capture', false);

        const w = videoElement.videoWidth || 1280;
        const h = videoElement.videoHeight || 720;
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        try {
            ctx.drawImage(videoElement, 0, 0, w, h);
        } catch (err) {
            console.error('Error drawing video frame:', err);
            return showSnapshotToast('Capture failed', false);
        }

        // Provide immediate visual feedback
        const captureBtn = document.getElementById('captureSnapshotBtn');
        if (captureBtn) {
            captureBtn.disabled = true;
            const prevText = captureBtn.textContent;
            captureBtn.textContent = 'Saving...';

            canvas.toBlob(async (blob) => {
                if (!blob) {
                    showSnapshotToast('Snapshot creation failed', false);
                    captureBtn.textContent = prevText;
                    captureBtn.disabled = false;
                    return;
                }

                const ts = new Date();
                const pad = (n) => String(n).padStart(2, '0');
                const filename = `snapshot_${ts.getFullYear()}${pad(ts.getMonth()+1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.png`;

                const form = new FormData();
                form.append('file', blob, filename);

                try {
                    const resp = await fetch('/api/upload_snapshot', { method: 'POST', body: form });
                    if (resp.ok) {
                        showSnapshotToast('Snapshot saved', true);
                    } else {
                        const text = await resp.text();
                        console.error('Upload failed', resp.status, text);
                        showSnapshotToast('Upload failed', false);
                    }
                } catch (err) {
                    console.error('Error uploading snapshot:', err);
                    showSnapshotToast('Upload error', false);
                }

                // Restore capture button
                captureBtn.textContent = prevText;
                captureBtn.disabled = false;
            }, 'image/png');
        } else {
            // If no capture button (shouldn't happen) still create blob and offer download
            canvas.toBlob((blob) => {
                if (!blob) return showSnapshotToast('Snapshot failed', false);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'snapshot.png';
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
                showSnapshotToast('Snapshot downloaded', true);
            }, 'image/png');
        }
    }

    function showSnapshotToast(message, ok = true) {
        const toast = document.getElementById('snapshotToast');
        if (!toast) {
            alert(message);
            return;
        }
        toast.textContent = message;
        toast.classList.add('show');
        toast.hidden = false;
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => { try { toast.hidden = true; } catch(e){} }, 220);
        }, 2200);
    }

    function handleSourceChange() {
        if (isStreaming) {
            stopFeed();
            // User would select different input and start again
        }
    }

    function startFpsCounter() {
        fpsCounter = 0;
        lastFpsTime = Date.now();

        function updateFps() {
            fpsCounter++;
            const now = Date.now();
            const elapsed = now - lastFpsTime;

            if (elapsed >= 1000) {
                const fps = Math.round((fpsCounter * 1000) / elapsed);
                document.getElementById('fpsValue').textContent = fps + ' FPS';
                fpsCounter = 0;
                lastFpsTime = now;
            }

            if (isStreaming) {
                animationId = requestAnimationFrame(updateFps);
            }
        }

        animationId = requestAnimationFrame(updateFps);
    }

    function stopFpsCounter() {
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', init);

})();
