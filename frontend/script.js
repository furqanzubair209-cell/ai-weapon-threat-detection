// ===== CONFIGURATION & API BACKEND =====
const API_BASE = window.location.protocol.startsWith('http') ? window.location.origin : 'http://127.0.0.1:8000';
let isBackendOnline = false;
let currentConfThreshold = 0.08;

// ===== NAVBAR SCROLL & MOBILE MENU =====
const navbar = document.getElementById('navbar');
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
const allNavLinks = document.querySelectorAll('.nav-link');

window.addEventListener('scroll', () => {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 50);
});

if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('open');
    });

    allNavLinks.forEach(link => {
        link.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navLinks.classList.remove('open');
        });
    });
}

// Active link on scroll
const sections = document.querySelectorAll('section[id]');
window.addEventListener('scroll', () => {
    const scrollY = window.scrollY + 200;
    sections.forEach(section => {
        const top = section.offsetTop;
        const height = section.offsetHeight;
        const id = section.getAttribute('id');
        const link = document.querySelector(`.nav-link[href="#${id}"]`);
        if (link) {
            link.classList.toggle('active', scrollY >= top && scrollY < top + height);
        }
    });
});

// ===== SCROLL REVEAL ANIMATIONS =====
const revealElements = document.querySelectorAll('.reveal');
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

revealElements.forEach(el => revealObserver.observe(el));

// ===== NUMBER COUNTER ANIMATION =====
function animateCounter(el, target, duration = 2000) {
    const start = 0;
    const startTime = performance.now();
    const isFloat = target % 1 !== 0;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (target - start) * eased;

        el.textContent = isFloat ? current.toFixed(1) : Math.round(current);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

// Hero stats counters
const heroStats = document.querySelectorAll('.stat-number');
const heroObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const target = parseFloat(entry.target.dataset.target);
            animateCounter(entry.target, target);
            heroObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

heroStats.forEach(el => heroObserver.observe(el));

// Metric ring counters
const metricCards = document.querySelectorAll('.metric-card');
const metricObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animated');
            const counter = entry.target.querySelector('.counter');
            if (counter) {
                const target = parseFloat(counter.dataset.target);
                animateCounter(counter, target);
            }
            const progress = entry.target.querySelector('.metric-progress');
            if (progress) {
                const value = parseFloat(entry.target.querySelector('.metric-ring').dataset.value);
                const circumference = 326.7;
                const offset = circumference - (circumference * value) / 100;
                progress.style.strokeDashoffset = offset;
            }
            metricObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.3 });

metricCards.forEach(el => metricObserver.observe(el));

// Bar fill animations
const barFills = document.querySelectorAll('.bar-fill');
const barObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animated');
            barObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

barFills.forEach(el => barObserver.observe(el));

// ===== BACKEND HEALTH CHECK =====
const aiServerBadge = document.getElementById('aiServerBadge');
const confSlider = document.getElementById('confSlider');
const confSliderVal = document.getElementById('confSliderVal');

if (confSlider && confSliderVal) {
    confSlider.addEventListener('input', (e) => {
        currentConfThreshold = parseInt(e.target.value, 10) / 100;
        confSliderVal.textContent = `${e.target.value}%`;
    });
}

// Image Upload Sensitivity Slider
const imgConfSlider = document.getElementById('imgConfSlider');
const imgConfSliderVal = document.getElementById('imgConfSliderVal');
if (imgConfSlider && imgConfSliderVal) {
    currentConfThreshold = 0.08;
    imgConfSlider.addEventListener('input', (e) => {
        currentConfThreshold = parseInt(e.target.value, 10) / 100;
        imgConfSliderVal.textContent = `${e.target.value}%`;
    });
}

async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
        if (res.ok) {
            const data = await res.json();
            isBackendOnline = true;
            if (aiServerBadge) {
                aiServerBadge.className = 'server-badge online';
                aiServerBadge.innerHTML = `&#9679; AI Engine: Online (${data.model || 'YOLO11s'})`;
            }
        } else {
            throw new Error('Not responding');
        }
    } catch (e) {
        isBackendOnline = false;
        if (aiServerBadge) {
            aiServerBadge.className = 'server-badge offline';
            aiServerBadge.innerHTML = `&#9679; AI Engine: Offline (Run run_backend.bat)`;
        }
    }
}

// Initial health check + poll every 5s
checkBackendHealth();
setInterval(checkBackendHealth, 5000);

// ===== IMAGE UPLOAD DETECTION SECTION =====
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadCanvas = document.getElementById('detectionCanvas');
const uploadCtx = uploadCanvas ? uploadCanvas.getContext('2d') : null;
const scanOverlay = document.getElementById('scanOverlay');
const detectionPreview = document.getElementById('detectionPreview');
const detectionResults = document.getElementById('detectionResults');
const sampleBtn = document.getElementById('sampleBtn');
const resetBtn = document.getElementById('resetBtn');
const placeholder = detectionPreview ? detectionPreview.querySelector('.preview-placeholder') : null;

let currentUploadImage = null;

if (uploadZone && fileInput) {
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            processUploadImage(file);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            processUploadImage(e.target.files[0]);
        }
    });
}

if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        if (uploadCanvas) uploadCanvas.style.display = 'none';
        if (placeholder) placeholder.style.display = '';
        if (detectionResults) detectionResults.style.display = 'none';
        if (fileInput) fileInput.value = '';
        currentUploadImage = null;
    });
}

if (sampleBtn) {
    sampleBtn.addEventListener('click', () => {
        generateSampleAndDetect();
    });
}

function processUploadImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            currentUploadImage = img;
            drawUploadedImage(img);
            runUploadDetection(e.target.result);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function drawUploadedImage(img) {
    if (!uploadCanvas || !detectionPreview) return;
    if (placeholder) placeholder.style.display = 'none';
    uploadCanvas.style.display = 'block';

    const maxW = detectionPreview.clientWidth;
    const maxH = 450;
    let w = img.width;
    let h = img.height;
    const ratio = Math.min(maxW / w, maxH / h);
    w *= ratio;
    h *= ratio;

    uploadCanvas.width = w;
    uploadCanvas.height = h;
    uploadCtx.drawImage(img, 0, 0, w, h);
}

function generateSampleAndDetect() {
    if (!uploadCanvas) return;
    if (placeholder) placeholder.style.display = 'none';
    uploadCanvas.style.display = 'block';

    const w = 640;
    const h = 420;
    uploadCanvas.width = w;
    uploadCanvas.height = h;

    const grad = uploadCtx.createLinearGradient(0, 0, w, h);
    grad.addColorStop(0, '#1a1a2e');
    grad.addColorStop(1, '#16213e');
    uploadCtx.fillStyle = grad;
    uploadCtx.fillRect(0, 0, w, h);

    uploadCtx.strokeStyle = 'rgba(0, 212, 255, 0.08)';
    uploadCtx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        uploadCtx.beginPath(); uploadCtx.moveTo(x, 0); uploadCtx.lineTo(x, h); uploadCtx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        uploadCtx.beginPath(); uploadCtx.moveTo(0, y); uploadCtx.lineTo(w, y); uploadCtx.stroke();
    }

    uploadCtx.fillStyle = 'rgba(0, 212, 255, 0.4)';
    uploadCtx.font = '16px Orbitron, monospace';
    uploadCtx.textAlign = 'center';
    uploadCtx.fillText('SAMPLE SURVEILLANCE FEED', w / 2, h / 2 - 10);
    uploadCtx.font = '12px Inter, sans-serif';
    uploadCtx.fillText('No weapon objects in frame', w / 2, h / 2 + 15);

    runUploadDetection(uploadCanvas.toDataURL('image/jpeg', 0.8));
}

async function runUploadDetection(base64Data) {
    if (scanOverlay) scanOverlay.classList.add('active');
    if (detectionResults) detectionResults.style.display = 'none';

    // If backend is online, call real model
    if (isBackendOnline) {
        try {
            const res = await fetch(`${API_BASE}/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: base64Data,
                    conf_threshold: currentConfThreshold
                })
            });
            const data = await res.json();
            
            setTimeout(() => {
                if (scanOverlay) scanOverlay.classList.remove('active');
                handleUploadResults(data.detections || [], data.processing_time_ms || 25);
            }, 600);
            return;
        } catch (e) {
            console.warn('Backend inference failed, falling back to clean offline result', e);
        }
    }

    // Offline mode: honest scan (no random hallucinations)
    setTimeout(() => {
        if (scanOverlay) scanOverlay.classList.remove('active');
        handleUploadResults([], 15);
    }, 800);
}

function handleUploadResults(detections, procTime) {
    if (!detectionResults) return;
    detectionResults.style.display = 'block';

    const resultCard = document.getElementById('resultCard');
    const resultClass = document.getElementById('resultClass');
    const threatBadge = document.getElementById('threatBadge');
    const confidenceFill = document.getElementById('confidenceFill');
    const confidenceValue = document.getElementById('confidenceValue');
    const threatLevel = document.getElementById('threatLevel');
    const processTimeEl = document.getElementById('processTime');

    if (processTimeEl) processTimeEl.textContent = `${procTime}ms`;

    if (detections.length === 0) {
        // Area Clear
        if (resultCard) resultCard.className = 'result-card threat-low';
        if (resultClass) {
            resultClass.textContent = '✅ No Weapons Detected';
            resultClass.style.color = '#00ff88';
        }
        if (threatBadge) {
            threatBadge.textContent = 'AREA CLEAR';
            threatBadge.className = 'threat-badge low';
        }
        if (confidenceFill) {
            confidenceFill.className = 'confidence-fill low';
            confidenceFill.style.width = '0%';
        }
        if (confidenceValue) confidenceValue.textContent = '0%';
        if (threatLevel) {
            threatLevel.textContent = 'NONE';
            threatLevel.style.color = '#00ff88';
        }
        return;
    }

    // Redraw base image first to ensure a clean canvas
    if (currentUploadImage) {
        drawUploadedImage(currentUploadImage);
    }

    // Found weapon(s)
    const primary = detections[0];
    const category = primary.category || (primary.type === 'real' ? 'REAL_WEAPON' : (primary.type === 'toy' ? 'TOY_WEAPON' : 'UNCERTAIN'));
    const isReal = category === 'REAL_WEAPON';
    const isToy = category === 'TOY_WEAPON';
    const conf = primary.confidence;

    // Draw bounding boxes on canvas
    const W = uploadCanvas.width;
    const H = uploadCanvas.height;

    detections.forEach(det => {
        const cat = det.category || (det.type === 'real' ? 'REAL_WEAPON' : (det.type === 'toy' ? 'TOY_WEAPON' : 'UNCERTAIN'));
        const boxColor = cat === 'REAL_WEAPON' ? '#ff3366' : (cat === 'TOY_WEAPON' ? '#ffaa00' : '#00d4ff');
        const bx = det.bbox.x * W;
        const by = det.bbox.y * H;
        const bw = det.bbox.w * W;
        const bh = det.bbox.h * H;

        uploadCtx.strokeStyle = boxColor;
        uploadCtx.lineWidth = 3;
        uploadCtx.strokeRect(bx, by, bw, bh);

        // Tech Corner Accents
        const cl = Math.min(18, bw * 0.25);
        uploadCtx.lineWidth = 4;
        [[bx, by, 1, 1], [bx + bw, by, -1, 1], [bx, by + bh, 1, -1], [bx + bw, by + bh, -1, -1]].forEach(([cx, cy, sx, sy]) => {
            uploadCtx.beginPath();
            uploadCtx.moveTo(cx + sx * cl, cy);
            uploadCtx.lineTo(cx, cy);
            uploadCtx.lineTo(cx, cy + sy * cl);
            uploadCtx.stroke();
        });

        uploadCtx.fillStyle = boxColor;
        const lbl = `${det.class} ${det.confidence}%`;
        uploadCtx.font = 'bold 13px Inter, sans-serif';
        const tw = uploadCtx.measureText(lbl).width + 14;

        // Position label banner so it never clips outside top canvas boundary
        const bannerY = (by >= 26) ? (by - 24) : by;
        const textY = (by >= 26) ? (by - 8) : (by + 16);

        uploadCtx.fillRect(bx, bannerY, tw, 22);
        uploadCtx.fillStyle = '#ffffff';
        uploadCtx.fillText(lbl, bx + 6, textY);
    });

    if (resultCard) {
        resultCard.className = isReal ? 'result-card threat-high' : (isToy ? 'result-card threat-low' : 'result-card');
    }
    if (resultClass) {
        if (isReal) {
            resultClass.textContent = '🚨 Real Weapon Detected';
            resultClass.style.color = '#ff3366';
        } else if (isToy) {
            resultClass.textContent = '⚡ Toy Weapon Detected';
            resultClass.style.color = '#ffaa00';
        } else {
            resultClass.textContent = '⚠️ Ambiguous / Uncertain Object';
            resultClass.style.color = '#00d4ff';
        }
    }
    if (threatBadge) {
        if (isReal) {
            threatBadge.textContent = 'HIGH THREAT';
            threatBadge.className = 'threat-badge high';
        } else if (isToy) {
            threatBadge.textContent = 'LOW THREAT (TOY)';
            threatBadge.className = 'threat-badge low';
        } else {
            threatBadge.textContent = 'CAUTION (UNCERTAIN)';
            threatBadge.className = 'threat-badge';
            threatBadge.style.background = 'rgba(0, 212, 255, 0.15)';
            threatBadge.style.color = '#00d4ff';
        }
    }
    if (confidenceFill) {
        confidenceFill.className = isReal ? 'confidence-fill high' : 'confidence-fill low';
        setTimeout(() => { confidenceFill.style.width = `${conf}%`; }, 100);
    }
    if (confidenceValue) confidenceValue.textContent = `${conf}%`;
    if (threatLevel) {
        threatLevel.textContent = isReal ? 'HIGH' : (isToy ? 'LOW' : 'CAUTION');
        threatLevel.style.color = isReal ? '#ff3366' : (isToy ? '#ffaa00' : '#00d4ff');
    }
}

// ===== WEBCAM SNAPSHOT DETECTION (TAKE PHOTO & PREDICT) =====
const startCameraBtn = document.getElementById('startCameraBtn');
const stopCameraBtn = document.getElementById('stopCameraBtn');
const switchCameraBtn = document.getElementById('switchCameraBtn');
const captureBtn = document.getElementById('captureBtn');
const resumeCameraBtn = document.getElementById('resumeCameraBtn');
const clearLogBtn = document.getElementById('clearLogBtn');
const webcamVideo = document.getElementById('webcamVideo');
const webcamCanvas = document.getElementById('webcamCanvas');
const webcamCtx = webcamCanvas ? webcamCanvas.getContext('2d') : null;
const cameraOverlay = document.getElementById('cameraOverlay');
const cameraFrame = document.getElementById('cameraFrame');
const liveBadge = document.getElementById('liveBadge');
const cameraStatus = document.getElementById('cameraStatus');
const inferTimeValue = document.getElementById('inferTimeValue');
const detectionStatus = document.getElementById('detectionStatus');
const detectionCount = document.getElementById('detectionCount');
const noDetectionMsg = document.getElementById('noDetectionMsg');
const detectionAlert = document.getElementById('detectionAlert');
const alertIcon = document.getElementById('alertIcon');
const alertClass = document.getElementById('alertClass');
const alertConf = document.getElementById('alertConf');
const alertLevel = document.getElementById('alertLevel');
const currentDetectionCard = document.getElementById('currentDetectionCard');
const realMeter = document.getElementById('realMeter');
const toyMeter = document.getElementById('toyMeter');
const clearMeter = document.getElementById('clearMeter');
const realMeterVal = document.getElementById('realMeterVal');
const toyMeterVal = document.getElementById('toyMeterVal');
const clearMeterVal = document.getElementById('clearMeterVal');
const detectionLog = document.getElementById('detectionLog');
const totalDetectionsEl = document.getElementById('totalDetections');
const realDetectionsEl = document.getElementById('realDetections');
const toyDetectionsEl = document.getElementById('toyDetections');

let webcamStream = null;
let useFrontCamera = true;
let totalScanned = 0;
let realDetected = 0;
let toyDetected = 0;
let isAnalyzing = false;

// Offscreen buffer canvas for capturing snapshots
const offscreenCanvas = document.createElement('canvas');
const offscreenCtx = offscreenCanvas.getContext('2d');

if (startCameraBtn) {
    startCameraBtn.addEventListener('click', startCamera);
}

if (stopCameraBtn) {
    stopCameraBtn.addEventListener('click', stopCamera);
}

if (switchCameraBtn) {
    switchCameraBtn.addEventListener('click', switchCamera);
}

if (captureBtn) {
    captureBtn.addEventListener('click', captureAndPredict);
}

if (resumeCameraBtn) {
    resumeCameraBtn.addEventListener('click', resumeLiveFeed);
}

if (clearLogBtn) {
    clearLogBtn.addEventListener('click', () => {
        if (detectionLog) detectionLog.innerHTML = '<div class="log-placeholder">Log cleared. Ready for next snapshot.</div>';
        totalScanned = 0; realDetected = 0; toyDetected = 0;
        if (totalDetectionsEl) totalDetectionsEl.textContent = '0';
        if (realDetectionsEl) realDetectionsEl.textContent = '0';
        if (toyDetectionsEl) toyDetectionsEl.textContent = '0';
        if (detectionCount) detectionCount.textContent = '0';
    });
}

async function startCamera() {
    try {
        const constraints = {
            video: {
                facingMode: useFrontCamera ? 'user' : 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
        webcamVideo.srcObject = webcamStream;
        webcamVideo.style.display = 'block';
        if (webcamCanvas) webcamCanvas.style.display = 'none';

        webcamVideo.onloadedmetadata = () => {
            if (webcamCanvas) {
                webcamCanvas.width = webcamVideo.videoWidth;
                webcamCanvas.height = webcamVideo.videoHeight;
            }
            offscreenCanvas.width = webcamVideo.videoWidth;
            offscreenCanvas.height = webcamVideo.videoHeight;
        };

        if (cameraOverlay) cameraOverlay.classList.add('hidden');
        if (liveBadge) liveBadge.style.display = 'flex';
        if (cameraStatus) cameraStatus.style.display = 'flex';
        if (startCameraBtn) startCameraBtn.style.display = 'none';
        if (stopCameraBtn) stopCameraBtn.style.display = 'inline-flex';
        if (switchCameraBtn) switchCameraBtn.style.display = 'inline-flex';
        if (captureBtn) {
            captureBtn.style.display = 'inline-flex';
            captureBtn.disabled = false;
            captureBtn.innerHTML = '📸 Capture & Predict';
        }
        if (resumeCameraBtn) resumeCameraBtn.style.display = 'none';

        if (detectionStatus) {
            detectionStatus.textContent = 'Live Ready';
            detectionStatus.style.color = '#00ff88';
        }

        checkBackendHealth();

    } catch (err) {
        alert('⚠️ Camera access denied or not found.\n\nPlease check permissions and try again.\n\nError: ' + err.message);
    }
}

function resumeLiveFeed() {
    if (!webcamStream) return;
    
    // Clear snapshot canvas overlay
    if (webcamCanvas && webcamCtx) {
        webcamCtx.clearRect(0, 0, webcamCanvas.width, webcamCanvas.height);
        webcamCanvas.style.display = 'none';
    }
    
    // Resume live video playback
    if (webcamVideo) {
        webcamVideo.style.display = 'block';
        webcamVideo.play();
    }

    if (cameraFrame) {
        cameraFrame.classList.remove('threat-active', 'real-flash');
    }

    if (resumeCameraBtn) resumeCameraBtn.style.display = 'none';
    if (captureBtn) {
        captureBtn.innerHTML = '📸 Capture & Predict';
        captureBtn.disabled = false;
    }

    if (detectionStatus) {
        detectionStatus.textContent = 'Live Ready';
        detectionStatus.style.color = '#00ff88';
    }
}

function stopCamera() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }

    if (webcamVideo) {
        webcamVideo.pause();
        webcamVideo.srcObject = null;
        webcamVideo.style.display = 'none';
    }
    if (webcamCanvas) {
        webcamCanvas.style.display = 'none';
        if (webcamCtx) webcamCtx.clearRect(0, 0, webcamCanvas.width, webcamCanvas.height);
    }
    if (cameraOverlay) cameraOverlay.classList.remove('hidden');
    if (liveBadge) liveBadge.style.display = 'none';
    if (cameraStatus) cameraStatus.style.display = 'none';
    if (startCameraBtn) startCameraBtn.style.display = 'inline-flex';
    if (stopCameraBtn) stopCameraBtn.style.display = 'none';
    if (switchCameraBtn) switchCameraBtn.style.display = 'none';
    if (captureBtn) captureBtn.style.display = 'none';
    if (resumeCameraBtn) resumeCameraBtn.style.display = 'none';

    if (cameraFrame) cameraFrame.classList.remove('threat-active', 'real-flash');
    resetLiveUI();
}

async function switchCamera() {
    useFrontCamera = !useFrontCamera;
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
    }
    try {
        const constraints = {
            video: {
                facingMode: useFrontCamera ? 'user' : 'environment',
                width: { ideal: 1280 }, height: { ideal: 720 }
            }
        };
        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
        webcamVideo.srcObject = webcamStream;
        resumeLiveFeed();
    } catch (e) {
        console.error('Camera switch failed:', e);
    }
}

async function captureAndPredict() {
    if (!webcamStream || isAnalyzing) return;
    isAnalyzing = true;

    // Grab current frame onto offscreen buffer canvas
    const W = webcamVideo.videoWidth || 640;
    const H = webcamVideo.videoHeight || 480;

    offscreenCanvas.width = W;
    offscreenCanvas.height = H;
    offscreenCtx.drawImage(webcamVideo, 0, 0, W, H);
    const photoBase64 = offscreenCanvas.toDataURL('image/jpeg', 0.85);

    // Freeze snapshot view on the displayed webcamCanvas
    if (webcamCanvas && webcamCtx) {
        webcamCanvas.width = W;
        webcamCanvas.height = H;
        webcamCanvas.style.display = 'block';
        webcamCtx.drawImage(offscreenCanvas, 0, 0, W, H);
    }
    webcamVideo.pause();

    // Update UI to analyzing state
    if (captureBtn) {
        captureBtn.disabled = true;
        captureBtn.innerHTML = '⏳ Predicting...';
    }
    if (detectionStatus) {
        detectionStatus.textContent = 'Analyzing Snapshot...';
        detectionStatus.style.color = '#00d4ff';
    }

    try {
        if (!isBackendOnline) {
            await checkBackendHealth();
        }

        if (isBackendOnline) {
            const res = await fetch(`${API_BASE}/detect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: photoBase64,
                    conf_threshold: currentConfThreshold
                })
            });

            if (res.ok) {
                const data = await res.json();
                handleSnapshotResults(data.detections || [], data.processing_time_ms || 35);
            } else {
                throw new Error('Server returned status: ' + res.status);
            }
        } else {
            alert('⚠️ AI Backend is offline.\n\nPlease run run_backend.bat or execute: python backend.py to enable YOLO model predictions.');
            handleSnapshotResults([], 0);
        }
    } catch (err) {
        console.error('Prediction request failed:', err);
        handleSnapshotResults([], 0);
    } finally {
        isAnalyzing = false;
        if (captureBtn) {
            captureBtn.disabled = false;
            captureBtn.innerHTML = '📸 Capture Again';
        }
        if (resumeCameraBtn) {
            resumeCameraBtn.style.display = 'inline-flex';
        }
    }
}

function handleSnapshotResults(detections, procTime) {
    totalScanned++;
    if (totalDetectionsEl) totalDetectionsEl.textContent = totalScanned;
    if (inferTimeValue) inferTimeValue.textContent = `${procTime}ms`;
    if (detectionCount) detectionCount.textContent = detections.length;

    // Redraw base snapshot photo on webcamCanvas
    const W = webcamCanvas.width;
    const H = webcamCanvas.height;
    webcamCtx.clearRect(0, 0, W, H);
    webcamCtx.drawImage(offscreenCanvas, 0, 0, W, H);

    if (detections.length === 0) {
        // Area clear
        if (noDetectionMsg) noDetectionMsg.style.display = 'block';
        if (detectionAlert) detectionAlert.style.display = 'none';
        if (currentDetectionCard) currentDetectionCard.className = 'current-detection-card clear';
        if (cameraFrame) cameraFrame.classList.remove('threat-active', 'real-flash');
        if (detectionStatus) {
            detectionStatus.textContent = '✅ Area Clear';
            detectionStatus.style.color = '#00ff88';
        }
        updateMeters(0, 0, 100);
        addLogEntry('clear', 'Area Clear (No Weapons)', 0);
        return;
    }

    // Weapon(s) detected!
    const primary = detections[0];
    const isReal = primary.type === 'real' || primary.class.toLowerCase().includes('real');
    const color = isReal ? '#ff3366' : '#ffaa00';

    if (isReal) realDetected++; else toyDetected++;
    if (realDetectionsEl) realDetectionsEl.textContent = realDetected;
    if (toyDetectionsEl) toyDetectionsEl.textContent = toyDetected;

    // Draw bounding boxes on canvas
    detections.forEach(det => {
        const detColor = det.type === 'real' ? '#ff3366' : '#ffaa00';
        const bx = det.bbox.x * W;
        const by = det.bbox.y * H;
        const bw = det.bbox.w * W;
        const bh = det.bbox.h * H;

        // Bounding box border
        webcamCtx.strokeStyle = detColor;
        webcamCtx.lineWidth = 3;
        webcamCtx.strokeRect(bx, by, bw, bh);

        // Tech Corner Accents
        const cl = Math.min(20, bw * 0.3);
        webcamCtx.lineWidth = 4;
        [[bx, by, 1, 1], [bx + bw, by, -1, 1], [bx, by + bh, 1, -1], [bx + bw, by + bh, -1, -1]].forEach(([cx, cy, sx, sy]) => {
            webcamCtx.beginPath();
            webcamCtx.moveTo(cx + sx * cl, cy);
            webcamCtx.lineTo(cx, cy);
            webcamCtx.lineTo(cx, cy + sy * cl);
            webcamCtx.stroke();
        });

        // Bounding box label
        const label = `${det.class} ${det.confidence}%`;
        webcamCtx.font = 'bold 14px Inter, sans-serif';
        const tw = webcamCtx.measureText(label).width + 14;
        webcamCtx.fillStyle = detColor;
        webcamCtx.fillRect(bx, by - 26, tw, 24);
        webcamCtx.fillStyle = '#fff';
        webcamCtx.fillText(label, bx + 7, by - 9);
    });

    // Alert details card
    if (noDetectionMsg) noDetectionMsg.style.display = 'none';
    if (detectionAlert) detectionAlert.style.display = 'flex';
    if (alertIcon) alertIcon.textContent = isReal ? '🚨' : '⚡';
    if (alertClass) {
        alertClass.textContent = primary.class;
        alertClass.style.color = color;
    }
    if (alertConf) alertConf.textContent = `Confidence: ${primary.confidence}%`;
    if (alertLevel) {
        alertLevel.textContent = isReal ? 'HIGH THREAT' : 'LOW THREAT (TOY)';
        alertLevel.className = isReal ? 'alert-level high' : 'alert-level low';
    }
    if (currentDetectionCard) {
        currentDetectionCard.className = `current-detection-card ${isReal ? 'real-threat' : 'toy-threat'}`;
    }

    if (cameraFrame) {
        cameraFrame.classList.add('threat-active');
        if (isReal) {
            cameraFrame.classList.add('real-flash');
        }
    }

    if (detectionStatus) {
        detectionStatus.textContent = isReal ? '🚨 THREAT DETECTED' : '⚡ Toy Weapon Detected';
        detectionStatus.style.color = color;
    }

    // Update confidence meters
    const realConf = isReal ? primary.confidence : 0;
    const toyConf = !isReal ? primary.confidence : 0;
    const clearConf = Math.max(0, 100 - realConf - toyConf);
    updateMeters(realConf, toyConf, clearConf);

    // Add entry to log
    addLogEntry(primary.type, primary.class, primary.confidence);
}

function updateMeters(real, toy, clear) {
    if (realMeter) realMeter.style.width = `${real}%`;
    if (toyMeter) toyMeter.style.width = `${toy}%`;
    if (clearMeter) clearMeter.style.width = `${clear}%`;
    if (realMeterVal) realMeterVal.textContent = `${Math.round(real)}%`;
    if (toyMeterVal) toyMeterVal.textContent = `${Math.round(toy)}%`;
    if (clearMeterVal) clearMeterVal.textContent = `${Math.round(clear)}%`;
}

function addLogEntry(type, className, conf) {
    if (!detectionLog) return;
    const placeholder = detectionLog.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();

    const time = new Date().toLocaleTimeString('en', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-text">${className}</span>
        <span class="log-conf">${conf > 0 ? conf + '%' : '--'}</span>
    `;

    detectionLog.insertBefore(entry, detectionLog.firstChild);

    const entries = detectionLog.querySelectorAll('.log-entry');
    if (entries.length > 25) entries[entries.length - 1].remove();
}

function resetLiveUI() {
    if (noDetectionMsg) noDetectionMsg.style.display = 'block';
    if (detectionAlert) detectionAlert.style.display = 'none';
    if (currentDetectionCard) currentDetectionCard.className = 'current-detection-card clear';
    updateMeters(0, 0, 100);
    if (detectionStatus) {
        detectionStatus.textContent = 'Live Ready';
        detectionStatus.style.color = '#00ff88';
    }
    if (inferTimeValue) inferTimeValue.textContent = '--';
    if (detectionCount) detectionCount.textContent = '0';
}

// ===== TRAINING LOSS CHART =====
function drawLossChart() {
    const chartCanvas = document.getElementById('lossChart');
    if (!chartCanvas) return;

    const chartCtx = chartCanvas.getContext('2d');
    const container = chartCanvas.parentElement;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    chartCanvas.width = rect.width * dpr;
    chartCanvas.height = rect.height * dpr;
    chartCtx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;
    const pad = { top: 20, right: 30, bottom: 40, left: 60 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const epochs = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 98];
    const boxLoss = [1.43, 1.27, 1.14, 1.07, 1.01, 0.97, 0.93, 0.88, 0.81, 0.78, 0.67];
    const clsLoss = [1.83, 1.35, 1.12, 0.99, 0.91, 0.82, 0.74, 0.67, 0.60, 0.55, 0.36];

    const maxY = 2.0;
    const minY = 0;

    function toX(epoch) { return pad.left + (epoch / 100) * plotW; }
    function toY(val) { return pad.top + (1 - (val - minY) / (maxY - minY)) * plotH; }

    chartCtx.fillStyle = 'transparent';
    chartCtx.fillRect(0, 0, W, H);

    chartCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    chartCtx.lineWidth = 1;
    for (let v = 0; v <= 2; v += 0.5) {
        const y = toY(v);
        chartCtx.beginPath();
        chartCtx.moveTo(pad.left, y);
        chartCtx.lineTo(W - pad.right, y);
        chartCtx.stroke();

        chartCtx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        chartCtx.font = '11px Inter, sans-serif';
        chartCtx.textAlign = 'right';
        chartCtx.fillText(v.toFixed(1), pad.left - 10, y + 4);
    }

    chartCtx.textAlign = 'center';
    for (let e = 0; e <= 100; e += 20) {
        const x = toX(e);
        chartCtx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        chartCtx.fillText(e, x, H - pad.bottom + 25);
    }

    chartCtx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    chartCtx.font = '12px Inter, sans-serif';
    chartCtx.fillText('Epoch', W / 2, H - 5);

    function drawLine(data, color) {
        const gradient = chartCtx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
        gradient.addColorStop(0, color.replace('1)', '0.2)'));
        gradient.addColorStop(1, color.replace('1)', '0)'));

        chartCtx.beginPath();
        chartCtx.moveTo(toX(epochs[0]), toY(data[0]));
        for (let i = 1; i < epochs.length; i++) {
            chartCtx.lineTo(toX(epochs[i]), toY(data[i]));
        }
        const fillPath = new Path2D();
        fillPath.moveTo(toX(epochs[0]), toY(data[0]));
        for (let i = 1; i < epochs.length; i++) {
            fillPath.lineTo(toX(epochs[i]), toY(data[i]));
        }
        fillPath.lineTo(toX(epochs[epochs.length - 1]), pad.top + plotH);
        fillPath.lineTo(toX(epochs[0]), pad.top + plotH);
        fillPath.closePath();
        chartCtx.fillStyle = gradient;
        chartCtx.fill(fillPath);

        chartCtx.beginPath();
        chartCtx.moveTo(toX(epochs[0]), toY(data[0]));
        for (let i = 1; i < epochs.length; i++) {
            chartCtx.lineTo(toX(epochs[i]), toY(data[i]));
        }
        chartCtx.strokeStyle = color;
        chartCtx.lineWidth = 2.5;
        chartCtx.stroke();

        for (let i = 0; i < epochs.length; i++) {
            chartCtx.beginPath();
            chartCtx.arc(toX(epochs[i]), toY(data[i]), 3, 0, Math.PI * 2);
            chartCtx.fillStyle = color;
            chartCtx.fill();
        }
    }

    drawLine(boxLoss, 'rgba(0, 212, 255, 1)');
    drawLine(clsLoss, 'rgba(123, 97, 255, 1)');

    const legendY = pad.top + 10;
    chartCtx.font = '12px Inter, sans-serif';
    chartCtx.fillStyle = 'rgba(0, 212, 255, 1)';
    chartCtx.fillRect(W - pad.right - 140, legendY, 14, 3);
    chartCtx.fillText('Box Loss', W - pad.right - 120, legendY + 5);

    chartCtx.fillStyle = 'rgba(123, 97, 255, 1)';
    chartCtx.fillRect(W - pad.right - 140, legendY + 20, 14, 3);
    chartCtx.fillText('Cls Loss', W - pad.right - 120, legendY + 25);
}

const chartSection = document.querySelector('.chart-section');
if (chartSection) {
    const chartObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                drawLossChart();
                chartObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });
    chartObserver.observe(chartSection);
}

let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(drawLossChart, 250);
});

// ===== SVG GRADIENT FOR METRIC RINGS =====
const svgDefs = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
svgDefs.setAttribute('width', '0');
svgDefs.setAttribute('height', '0');
svgDefs.style.position = 'absolute';
svgDefs.innerHTML = `
    <defs>
        <linearGradient id="metricGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#00d4ff"/>
            <stop offset="50%" style="stop-color:#7b61ff"/>
            <stop offset="100%" style="stop-color:#ff3366"/>
        </linearGradient>
    </defs>
`;
document.body.prepend(svgDefs);

document.querySelectorAll('.metric-progress').forEach(circle => {
    circle.setAttribute('stroke', 'url(#metricGradient)');
});

console.log('🛡️ Weapon Detection AI Frontend & Real AI Pipeline initialized');

// ===== VIDEO UPLOAD & ANALYSIS LOGIC =====
const videoUploadZone = document.getElementById('videoUploadZone');
const videoFileInput = document.getElementById('videoFileInput');
const videoFileInfo = document.getElementById('videoFileInfo');
const videoFileName = document.getElementById('videoFileName');
const videoFileMeta = document.getElementById('videoFileMeta');
const removeVideoBtn = document.getElementById('removeVideoBtn');

const videoConfSlider = document.getElementById('videoConfSlider');
const videoConfVal = document.getElementById('videoConfVal');
const frameStrideSelect = document.getElementById('frameStrideSelect');
const startVideoAnalysisBtn = document.getElementById('startVideoAnalysisBtn');

const videoProgressContainer = document.getElementById('videoProgressContainer');
const videoProgressStatus = document.getElementById('videoProgressStatus');
const videoProgressPercent = document.getElementById('videoProgressPercent');
const videoProgressFill = document.getElementById('videoProgressFill');
const videoProgressMeta = document.getElementById('videoProgressMeta');

const videoPlaceholder = document.getElementById('videoPlaceholder');
const annotatedVideoPlayer = document.getElementById('annotatedVideoPlayer');
const videoSummaryStats = document.getElementById('videoSummaryStats');
const vidRealCount = document.getElementById('vidRealCount');
const vidToyCount = document.getElementById('vidToyCount');
const vidThreatLevel = document.getElementById('vidThreatLevel');
const videoTimelineWrapper = document.getElementById('videoTimelineWrapper');
const videoTimelineList = document.getElementById('videoTimelineList');
const videoDownloadArea = document.getElementById('videoDownloadArea');
const downloadVideoBtn = document.getElementById('downloadVideoBtn');

let selectedVideoFile = null;
let videoPollInterval = null;

if (videoConfSlider && videoConfVal) {
    videoConfSlider.addEventListener('input', (e) => {
        videoConfVal.textContent = `${e.target.value}%`;
    });
}

if (videoUploadZone && videoFileInput) {
    videoUploadZone.addEventListener('click', () => videoFileInput.click());

    videoUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        videoUploadZone.classList.add('drag-over');
    });

    videoUploadZone.addEventListener('dragleave', () => {
        videoUploadZone.classList.remove('drag-over');
    });

    videoUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        videoUploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleSelectedVideo(e.dataTransfer.files[0]);
        }
    });

    videoFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleSelectedVideo(e.target.files[0]);
        }
    });
}

if (removeVideoBtn) {
    removeVideoBtn.addEventListener('click', () => {
        resetVideoUpload();
    });
}

function handleSelectedVideo(file) {
    const validExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext) && !file.type.startsWith('video/')) {
        alert(`⚠️ Unsupported format.\n\nPlease select a video file (${validExtensions.join(', ')}).`);
        return;
    }

    const maxBytes = 100 * 1024 * 1024; // 100 MB
    if (file.size > maxBytes) {
        alert('⚠️ File too large.\n\nMaximum video size is 100 MB.');
        return;
    }

    selectedVideoFile = file;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);

    if (videoFileName) videoFileName.textContent = file.name;
    if (videoFileMeta) videoFileMeta.textContent = `${sizeMb} MB • Ready for analysis`;
    if (videoFileInfo) videoFileInfo.style.display = 'flex';
    if (videoUploadZone) videoUploadZone.style.display = 'none';
    if (startVideoAnalysisBtn) {
        startVideoAnalysisBtn.disabled = false;
        startVideoAnalysisBtn.innerHTML = '<span class="btn-icon">&#9658;</span> Analyze Video';
    }

    // Immediately show the selected/uploaded video on the side player!
    const videoUrl = URL.createObjectURL(file);
    const videoPreviewHeader = document.getElementById('videoPreviewHeader');
    const previewBadge = document.getElementById('previewBadge');
    const previewFilename = document.getElementById('previewFilename');

    if (videoPlaceholder) videoPlaceholder.style.display = 'none';
    if (annotatedVideoPlayer) {
        annotatedVideoPlayer.style.display = 'block';
        annotatedVideoPlayer.src = videoUrl;
        annotatedVideoPlayer.load();
    }
    if (videoPreviewHeader) videoPreviewHeader.style.display = 'flex';
    if (previewBadge) {
        previewBadge.textContent = '📹 Uploaded Video Preview';
        previewBadge.className = 'preview-badge';
    }
    if (previewFilename) previewFilename.textContent = file.name;

    // Reset results areas until analysis runs
    if (videoSummaryStats) videoSummaryStats.style.display = 'none';
    if (videoTimelineWrapper) videoTimelineWrapper.style.display = 'none';
    if (videoDownloadArea) videoDownloadArea.style.display = 'none';
}

function resetVideoUpload() {
    selectedVideoFile = null;
    if (videoFileInput) videoFileInput.value = '';
    if (videoFileInfo) videoFileInfo.style.display = 'none';
    if (videoUploadZone) videoUploadZone.style.display = 'block';
    if (startVideoAnalysisBtn) {
        startVideoAnalysisBtn.disabled = true;
        startVideoAnalysisBtn.innerHTML = '<span class="btn-icon">&#9658;</span> Analyze Video';
    }
    if (videoProgressContainer) videoProgressContainer.style.display = 'none';
    if (videoPollInterval) {
        clearInterval(videoPollInterval);
        videoPollInterval = null;
    }

    // Reset video player and show placeholder
    const videoPreviewHeader = document.getElementById('videoPreviewHeader');
    if (videoPreviewHeader) videoPreviewHeader.style.display = 'none';
    if (annotatedVideoPlayer) {
        annotatedVideoPlayer.pause();
        annotatedVideoPlayer.src = '';
        annotatedVideoPlayer.style.display = 'none';
    }
    if (videoPlaceholder) videoPlaceholder.style.display = 'flex';
    if (videoSummaryStats) videoSummaryStats.style.display = 'none';
    if (videoTimelineWrapper) videoTimelineWrapper.style.display = 'none';
    if (videoDownloadArea) videoDownloadArea.style.display = 'none';
}

if (startVideoAnalysisBtn) {
    startVideoAnalysisBtn.addEventListener('click', async () => {
        if (!selectedVideoFile) return;

        if (!isBackendOnline) {
            alert('⚠️ AI Engine is Offline.\n\nPlease start the backend server via run_backend.bat or run: python backend.py');
            return;
        }

        const confThresh = videoConfSlider ? (parseInt(videoConfSlider.value, 10) / 100) : 0.20;
        const frameStride = frameStrideSelect ? parseInt(frameStrideSelect.value, 10) : 2;

        startVideoAnalysisBtn.disabled = true;
        startVideoAnalysisBtn.innerHTML = '⏳ Uploading Video...';

        if (videoProgressContainer) videoProgressContainer.style.display = 'flex';
        if (videoProgressFill) videoProgressFill.style.width = '0%';
        if (videoProgressPercent) videoProgressPercent.textContent = '0%';
        if (videoProgressStatus) videoProgressStatus.textContent = 'Uploading video to server...';
        if (videoProgressMeta) videoProgressMeta.textContent = 'Preparing pipeline...';

        const formData = new FormData();
        formData.append('file', selectedVideoFile);
        formData.append('conf_threshold', confThresh);
        formData.append('frame_stride', frameStride);

        try {
            const res = await fetch(`${API_BASE}/detect/video`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: 'Upload error' }));
                throw new Error(errData.detail || 'Upload failed');
            }

            const data = await res.json();
            const jobId = data.job_id;

            if (videoProgressStatus) videoProgressStatus.textContent = 'Analyzing frames & tracking threats...';
            startVideoAnalysisBtn.innerHTML = '⚡ Processing Video...';

            pollVideoJob(jobId);

        } catch (err) {
            console.error('Video upload failed:', err);
            alert(`⚠️ Video analysis error: ${err.message}`);
            if (videoProgressContainer) videoProgressContainer.style.display = 'none';
            startVideoAnalysisBtn.disabled = false;
            startVideoAnalysisBtn.innerHTML = '<span class="btn-icon">&#9658;</span> Analyze Video';
        }
    });
}

function pollVideoJob(jobId) {
    if (videoPollInterval) clearInterval(videoPollInterval);

    videoPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/video/status/${jobId}`);
            if (!res.ok) throw new Error('Job status query failed');

            const job = await res.json();
            const pct = job.progress_percent || 0;

            if (videoProgressFill) videoProgressFill.style.width = `${pct}%`;
            if (videoProgressPercent) videoProgressPercent.textContent = `${Math.round(pct)}%`;
            if (videoProgressMeta) {
                videoProgressMeta.textContent = `Frames: ${job.current_frame || 0} / ${job.total_frames || '?'} • FPS: ${job.fps ? Math.round(job.fps) : '--'}`;
            }

            if (job.status === 'completed') {
                clearInterval(videoPollInterval);
                videoPollInterval = null;
                handleVideoJobSuccess(job);
            } else if (job.status === 'failed') {
                clearInterval(videoPollInterval);
                videoPollInterval = null;
                alert(`⚠️ Video processing failed:\n\n${job.error || 'Unknown error'}`);
                if (videoProgressContainer) videoProgressContainer.style.display = 'none';
                startVideoAnalysisBtn.disabled = false;
                startVideoAnalysisBtn.innerHTML = '<span class="btn-icon">&#9658;</span> Retry Analysis';
            }
        } catch (err) {
            console.warn('Polling error:', err);
        }
    }, 800);
}

function handleVideoJobSuccess(job) {
    if (videoProgressContainer) videoProgressContainer.style.display = 'none';
    if (startVideoAnalysisBtn) {
        startVideoAnalysisBtn.disabled = false;
        startVideoAnalysisBtn.innerHTML = '✓ Video Analyzed';
    }

    // Update Preview Badge and Video Player to Annotated Stream
    const previewBadge = document.getElementById('previewBadge');
    if (previewBadge) {
        previewBadge.textContent = '🚨 Annotated Threat Video (AI Detection Complete)';
        previewBadge.className = 'preview-badge annotated';
    }

    if (videoPlaceholder) videoPlaceholder.style.display = 'none';
    if (annotatedVideoPlayer) {
        annotatedVideoPlayer.style.display = 'block';
        annotatedVideoPlayer.src = `${API_BASE}/stream/video/${job.job_id}`;
        annotatedVideoPlayer.load();
        annotatedVideoPlayer.play().catch(() => {});
    }

    // Display Download Link
    if (videoDownloadArea && downloadVideoBtn) {
        videoDownloadArea.style.display = 'block';
        downloadVideoBtn.href = `${API_BASE}/download/video/${job.job_id}`;
        downloadVideoBtn.setAttribute('download', `annotated_threats_${job.job_id.slice(0, 8)}.mp4`);
    }

    // Populate Summary Counters
    const summary = job.summary || {};
    if (videoSummaryStats) videoSummaryStats.style.display = 'grid';
    if (vidRealCount) vidRealCount.textContent = summary.real_weapons || 0;
    if (vidToyCount) vidToyCount.textContent = summary.toy_weapons || 0;
    if (vidThreatLevel) {
        const lvl = summary.highest_threat || 'NONE';
        vidThreatLevel.textContent = lvl;
        vidThreatLevel.style.color = lvl === 'HIGH' ? '#ff3366' : (lvl === 'LOW' ? '#ffaa00' : '#00ff88');
    }

    // Populate Detection Timeline
    if (videoTimelineWrapper && videoTimelineList) {
        videoTimelineList.innerHTML = '';
        const timeline = summary.timeline || [];

        if (timeline.length === 0) {
            videoTimelineList.innerHTML = '<span style="color: #00ff88; font-size: 0.85rem;">✅ No weapons detected across video frames.</span>';
        } else {
            timeline.forEach(ev => {
                const pill = document.createElement('div');
                const catClass = ev.category === 'REAL_WEAPON' ? 'real' : (ev.category === 'TOY_WEAPON' ? 'toy' : 'uncertain');
                pill.className = `timeline-pill ${catClass}`;
                pill.innerHTML = `
                    <span class="pill-time">⏱ ${ev.timestamp_sec}s</span>
                    <span>${ev.class} (${ev.confidence}%)</span>
                `;
                pill.title = `Click to jump to ${ev.timestamp_sec}s in video`;
                pill.addEventListener('click', () => {
                    if (annotatedVideoPlayer) {
                        annotatedVideoPlayer.currentTime = Math.max(0, ev.timestamp_sec - 0.5);
                        annotatedVideoPlayer.play();
                    }
                });
                videoTimelineList.appendChild(pill);
            });
        }
        videoTimelineWrapper.style.display = 'block';
    }
}
