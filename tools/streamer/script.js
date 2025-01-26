const PANEL_WIDTH = 40;
const PANEL_HEIGHT = 96;
const FRAME_SIZE = PANEL_WIDTH * PANEL_HEIGHT * 3;  // RGB
const CHUNK_SIZE = 1024;
const TARGET_FPS = 30;
const FRAME_TIME = 1000 / TARGET_FPS;
const PREVIEW_WIDTH = PANEL_WIDTH;
const PREVIEW_HEIGHT = PANEL_HEIGHT;

let port;
let isStreaming = false;
let frameCount = 0;
let lastFpsTime = 0;
let streamInterval;
let contrast = 1.0;
let brightness = 0;
let shouldLoop = true;
let videoLoop;
let originalFileName = '';
let shadows = 0;
let midtones = 0;
let highlights = 0;
let redChannel = 1.0;
let greenChannel = 1.0;
let blueChannel = 1.0;
let isConnected = false;
let trimStart = 0;
let trimEnd = 0;
let xOffset = 0;  // -100 to 100 percentage

const video = document.getElementById('preview');
const canvas = document.getElementById('processCanvas');
const ctx = canvas.getContext('2d', { willReadFrequently: true });
const previewCanvas = document.getElementById('previewCanvas');
const previewCtx = previewCanvas.getContext('2d', { willReadFrequently: true });

// Set up canvases with correct dimensions
canvas.width = PANEL_WIDTH;
canvas.height = PANEL_HEIGHT;
previewCanvas.width = PREVIEW_WIDTH;
previewCanvas.height = PREVIEW_HEIGHT;

// Start the preview loop immediately
requestAnimationFrame(updatePreview);

// Add this to make sure preview updates when video loads
video.addEventListener('loadedmetadata', () => {
    if (!isStreaming) {
        requestAnimationFrame(updatePreview);
    }
});

async function toggleConnection() {
    if (!isConnected) {
        try {
            port = await navigator.serial.requestPort();
            await port.open({ baudRate: 2000000 });

            isConnected = true;
            document.getElementById('connectButton').textContent = 'Disconnect';
            document.getElementById('status').className = 'success';
            document.getElementById('status').textContent = 'Connected to Teensy';
            document.getElementById('streamButton').disabled = !video.src;  // Only enable if we have a video
        } catch (error) {
            document.getElementById('status').className = 'error';
            document.getElementById('status').textContent = 'Connection failed: ' + error;
        }
    } else {
        try {
            // Stop streaming if active
            if (isStreaming) {
                isStreaming = false;
                clearTimeout(videoLoop);
                video.pause();
            }

            // Close the port
            await port.close();
            port = null;

            isConnected = false;
            document.getElementById('connectButton').textContent = 'Connect to Teensy';
            document.getElementById('status').className = 'info';
            document.getElementById('status').textContent = 'Disconnected from Teensy';
            document.getElementById('streamButton').disabled = true;  // Always disable when disconnected
            document.getElementById('stopButton').disabled = true;
        } catch (error) {
            document.getElementById('status').className = 'error';
            document.getElementById('status').textContent = 'Disconnect failed: ' + error;
        }
    }
}

function adjustPixel(value, contrast, brightness, channel) {
    // Apply contrast
    let newValue = ((value / 255 - 0.5) * contrast + 0.5) * 255;

    // Apply brightness
    newValue += brightness;

    // Apply tone adjustments
    const normalizedValue = newValue / 255;

    // Shadows affect dark areas (0-0.33)
    if (normalizedValue <= 0.33) {
        newValue += shadows * (1 - normalizedValue * 3);
    }

    // Midtones affect middle range (0.33-0.66)
    if (normalizedValue > 0.33 && normalizedValue < 0.66) {
        const midFactor = 1 - Math.abs(normalizedValue - 0.5) * 3;
        newValue += midtones * midFactor;
    }

    // Highlights affect bright areas (0.66-1.0)
    if (normalizedValue >= 0.66) {
        newValue += highlights * ((normalizedValue - 0.66) * 3);
    }

    // Apply channel adjustment
    newValue *= channel;

    // Clamp value between 0 and 255
    return Math.max(0, Math.min(255, newValue));
}

// Modify the calculateCrop function to include xOffset
function calculateCrop(videoWidth, videoHeight) {
    const targetAspect = PANEL_WIDTH / PANEL_HEIGHT;
    const videoAspect = videoWidth / videoHeight;

    let sourceX = 0;
    let sourceY = 0;
    let sourceWidth = videoWidth;
    let sourceHeight = videoHeight;

    if (videoAspect > targetAspect) {
        // Video is wider than target - crop sides
        sourceWidth = videoHeight * targetAspect;

        // Calculate the maximum possible offset
        const maxOffset = (videoWidth - sourceWidth);

        // Apply the offset based on percentage (-100 to 100)
        sourceX = (videoWidth - sourceWidth) / 2;  // Center position
        sourceX += (maxOffset / 2) * (xOffset / 100);  // Add offset

        // Clamp sourceX to prevent going out of bounds
        sourceX = Math.max(0, Math.min(videoWidth - sourceWidth, sourceX));
    } else if (videoAspect < targetAspect) {
        // Video is taller than target - crop top/bottom
        sourceHeight = videoWidth / targetAspect;
        sourceY = (videoHeight - sourceHeight) / 2;
    }

    return { sourceX, sourceY, sourceWidth, sourceHeight };
}

// Modify the processVideoFrame function
function processVideoFrame() {
    const crop = calculateCrop(video.videoWidth, video.videoHeight);

    // Draw with crop
    ctx.drawImage(video,
        crop.sourceX, crop.sourceY, crop.sourceWidth, crop.sourceHeight,
        0, 0, PANEL_WIDTH, PANEL_HEIGHT
    );

    const imageData = ctx.getImageData(0, 0, PANEL_WIDTH, PANEL_HEIGHT);
    const data = imageData.data;
    const rgbData = new Uint8Array(PANEL_WIDTH * PANEL_HEIGHT * 3);
    let rgbIndex = 0;

    for (let i = 0; i < data.length; i += 4) {
        rgbData[rgbIndex++] = adjustPixel(data[i], contrast, brightness, redChannel);     // R
        rgbData[rgbIndex++] = adjustPixel(data[i + 1], contrast, brightness, greenChannel); // G
        rgbData[rgbIndex++] = adjustPixel(data[i + 2], contrast, brightness, blueChannel);  // B
    }

    return rgbData;
}

async function streamVideo() {
    if (!isStreaming || !port) return;

    const now = performance.now();

    // Process current frame
    const frameData = processVideoFrame();

    try {
        // Send frame in chunks
        for (let i = 0; i < frameData.length; i += CHUNK_SIZE) {
            const chunk = frameData.slice(i, i + CHUNK_SIZE);
            const writer = port.writable.getWriter();
            await writer.write(chunk);
            writer.releaseLock();
            await new Promise(resolve => setTimeout(resolve, 1));
        }

        // Update FPS counter
        frameCount++;
        if (now - lastFpsTime >= 1000) {
            const fps = frameCount;
            document.getElementById('fps').textContent = `FPS: ${fps}`;
            frameCount = 0;
            lastFpsTime = now;
        }

        // Schedule next frame
        if (isStreaming) {
            const elapsed = performance.now() - now;
            const delay = Math.max(0, FRAME_TIME - elapsed);
            videoLoop = setTimeout(streamVideo, delay);
        }
    } catch (error) {
        console.error('Streaming error:', error);
        isStreaming = false;
        document.getElementById('streamButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Streaming error: ' + error.message;
    }
}

// Modify the convertToBin function to use trim points
async function convertToBin() {
    if (!video.src) {
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Please select a video file';
        return;
    }

    const progressBar = document.getElementById('conversionProgress');
    const progressFill = progressBar.querySelector('.progress-fill');
    const progressText = progressBar.querySelector('.progress-text');

    progressBar.style.display = 'block';
    document.getElementById('downloadBinButton').disabled = true;
    document.getElementById('status').className = 'info';
    document.getElementById('status').textContent = 'Converting video to binary...';

    // Calculate frames from trim points
    const startFrame = Math.floor(trimStart * TARGET_FPS);
    const endFrame = Math.floor(trimEnd * TARGET_FPS);
    const totalFrames = endFrame - startFrame;
    let currentFrame = 0;

    // Create a buffer to hold trimmed frames
    const binData = new Uint8Array(totalFrames * FRAME_SIZE);
    let binOffset = 0;

    // Save current video time and playback state
    const originalTime = video.currentTime;
    const wasPlaying = !video.paused;
    if (wasPlaying) {
        video.pause();
    }

    try {
        // Process each frame within trim points
        for (let i = startFrame; i < endFrame; i++) {
            // Set video to exact frame time
            const frameTime = i / TARGET_FPS;

            // Wait for the video to update to the current frame
            await new Promise(resolve => {
                video.onseeked = resolve;
                video.currentTime = frameTime;
            });

            // Process frame with current settings
            const frameData = processVideoFrame();

            // Add to binary buffer
            binData.set(frameData, binOffset);
            binOffset += frameData.length;

            // Update progress
            currentFrame++;
            const progress = Math.floor((currentFrame / totalFrames) * 100);
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;
        }

        // Create and download the binary file
        const blob = new Blob([binData], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Add trim info to filename
        const nameWithoutExt = originalFileName.split('.')[0];
        const trimInfo = `_${trimStart.toFixed(1)}s-${trimEnd.toFixed(1)}s`;
        a.download = `${nameWithoutExt}${trimInfo}.bin`;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        document.getElementById('status').className = 'success';
        document.getElementById('status').textContent = 'Binary file downloaded!';
    } catch (error) {
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Error converting video: ' + error.message;
    } finally {
        // Restore video state
        video.currentTime = originalTime;
        if (wasPlaying && isStreaming) {
            video.play();
        }
        document.getElementById('downloadBinButton').disabled = false;
        progressBar.style.display = 'none';
    }
}

// Event Listeners
document.getElementById('connectButton').onclick = toggleConnection;

document.getElementById('fileInput').onchange = (event) => {
    const file = event.target.files[0];
    if (file) {
        originalFileName = file.name;  // Store the original filename
        video.src = URL.createObjectURL(file);
        document.getElementById('streamButton').disabled = !isConnected;  // Only enable if connected
        document.getElementById('stopButton').disabled = true;
        document.getElementById('downloadBinButton').disabled = false;
    }
};

document.getElementById('streamButton').onclick = () => {
    if (!video.src) {
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Please select a video file';
        return;
    }

    if (!port) {
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Please connect to Teensy first';
        return;
    }

    isStreaming = true;
    video.loop = shouldLoop;
    video.play();

    // Clear the preview canvas when starting stream
    previewCtx.clearRect(0, 0, PREVIEW_WIDTH, PREVIEW_HEIGHT);

    document.getElementById('streamButton').disabled = true;
    document.getElementById('stopButton').disabled = false;
    document.getElementById('status').className = 'info';
    document.getElementById('status').textContent = 'Streaming video...';
    streamVideo();
};

document.getElementById('stopButton').onclick = () => {
    isStreaming = false;
    clearTimeout(videoLoop);
    video.pause();
    document.getElementById('streamButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
    document.getElementById('status').className = 'info';
    document.getElementById('status').textContent = 'Streaming stopped';
};

document.getElementById('contrast').oninput = (event) => {
    contrast = event.target.value / 100;
    document.getElementById('contrastValue').textContent = contrast.toFixed(1);
    updateControls();
};

document.getElementById('brightness').oninput = (event) => {
    brightness = parseInt(event.target.value);
    document.getElementById('brightnessValue').textContent = brightness;
    updateControls();
};

document.getElementById('shadows').oninput = (event) => {
    shadows = parseInt(event.target.value);
    document.getElementById('shadowsValue').textContent = shadows;
    updateControls();
};

document.getElementById('midtones').oninput = (event) => {
    midtones = parseInt(event.target.value);
    document.getElementById('midtonesValue').textContent = midtones;
    updateControls();
};

document.getElementById('highlights').oninput = (event) => {
    highlights = parseInt(event.target.value);
    document.getElementById('highlightsValue').textContent = highlights;
    updateControls();
};

document.getElementById('loopVideo').onchange = (event) => {
    shouldLoop = event.target.checked;
    video.loop = shouldLoop;
    updateControls();
};

document.getElementById('downloadBinButton').onclick = convertToBin;

// Check WebSerial support
if (!navigator.serial) {
    document.getElementById('status').className = 'error';
    document.getElementById('status').textContent =
        'WebSerial is not supported in this browser. Please use Chrome or Edge.';
    document.getElementById('connectButton').disabled = true;
}

// Add video ended event handler
video.addEventListener('ended', () => {
    if (!shouldLoop) {
        isStreaming = false;
        clearTimeout(videoLoop);
        document.getElementById('streamButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
        document.getElementById('status').className = 'info';
        document.getElementById('status').textContent = 'Playback finished';
    }
});

// Modify the updatePreview function
function updatePreview() {
    if (video.readyState >= 2 && !isStreaming) {
        const crop = calculateCrop(video.videoWidth, video.videoHeight);

        // Draw at panel resolution with crop
        previewCtx.drawImage(video,
            crop.sourceX, crop.sourceY, crop.sourceWidth, crop.sourceHeight,
            0, 0, PANEL_WIDTH, PANEL_HEIGHT
        );

        // Process the image
        const imageData = previewCtx.getImageData(0, 0, PANEL_WIDTH, PANEL_HEIGHT);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            data[i] = adjustPixel(data[i], contrast, brightness, redChannel);     // R
            data[i + 1] = adjustPixel(data[i + 1], contrast, brightness, greenChannel); // G
            data[i + 2] = adjustPixel(data[i + 2], contrast, brightness, blueChannel);  // B
            // Alpha channel remains unchanged
        }

        previewCtx.putImageData(imageData, 0, 0);
    }

    if (!video.paused) {
        requestAnimationFrame(updatePreview);
    }
}

// Replace the updateControls function with this:
function updateControls() {
    if (!isStreaming && !video.paused) {
        requestAnimationFrame(updatePreview);
    } else if (!isStreaming) {
        // If video is paused, update once
        updatePreview();
    }
}

// Add these video event listeners after the other event listeners
video.addEventListener('play', () => {
    if (!isStreaming) {
        requestAnimationFrame(updatePreview);
    }
});

video.addEventListener('pause', () => {
    // Update one last time when paused
    if (!isStreaming) {
        updatePreview();
    }
});

// Add event listeners for the RGB controls
document.getElementById('red').oninput = (event) => {
    redChannel = event.target.value / 100;
    document.getElementById('redValue').textContent = Math.round(redChannel * 100);
    updateControls();
};

document.getElementById('green').oninput = (event) => {
    greenChannel = event.target.value / 100;
    document.getElementById('greenValue').textContent = Math.round(greenChannel * 100);
    updateControls();
};

document.getElementById('blue').oninput = (event) => {
    blueChannel = event.target.value / 100;
    document.getElementById('blueValue').textContent = Math.round(blueChannel * 100);
    updateControls();
};

// Add this function to update trim controls
function updateTrimControls() {
    const duration = video.duration || 0;
    const startSlider = document.getElementById('trimStart');
    const endSlider = document.getElementById('trimEnd');
    const startNum = document.getElementById('trimStartNum');
    const endNum = document.getElementById('trimEndNum');

    // Update slider ranges
    startSlider.max = duration;
    endSlider.max = duration;
    startNum.max = duration;
    endNum.max = duration;

    // Set end value to duration if not set
    if (trimEnd === 0) {
        trimEnd = duration;
        endSlider.value = duration;
        endNum.value = duration.toFixed(1);
    }
}

// Add these event listeners
video.addEventListener('loadedmetadata', updateTrimControls);

document.getElementById('trimStart').oninput = (event) => {
    trimStart = parseFloat(event.target.value);
    document.getElementById('trimStartNum').value = trimStart.toFixed(1);
    if (trimStart >= trimEnd) {
        trimStart = trimEnd - 0.1;
        event.target.value = trimStart;
        document.getElementById('trimStartNum').value = trimStart.toFixed(1);
    }
    if (!isStreaming && video.currentTime < trimStart) {
        video.currentTime = trimStart;
    }
};

document.getElementById('trimEnd').oninput = (event) => {
    trimEnd = parseFloat(event.target.value);
    document.getElementById('trimEndNum').value = trimEnd.toFixed(1);
    if (trimEnd <= trimStart) {
        trimEnd = trimStart + 0.1;
        event.target.value = trimEnd;
        document.getElementById('trimEndNum').value = trimEnd.toFixed(1);
    }
};

document.getElementById('trimStartNum').onchange = (event) => {
    trimStart = Math.max(0, Math.min(parseFloat(event.target.value), trimEnd - 0.1));
    event.target.value = trimStart.toFixed(1);
    document.getElementById('trimStart').value = trimStart;
    if (!isStreaming && video.currentTime < trimStart) {
        video.currentTime = trimStart;
    }
};

document.getElementById('trimEndNum').onchange = (event) => {
    trimEnd = Math.min(video.duration, Math.max(trimStart + 0.1, parseFloat(event.target.value)));
    event.target.value = trimEnd.toFixed(1);
    document.getElementById('trimEnd').value = trimEnd;
};

// Modify the video ended event handler
video.addEventListener('timeupdate', () => {
    if (video.currentTime >= trimEnd) {
        if (shouldLoop) {
            video.currentTime = trimStart;
        } else {
            video.pause();
            if (isStreaming) {
                isStreaming = false;
                clearTimeout(videoLoop);
                document.getElementById('streamButton').disabled = false;
                document.getElementById('stopButton').disabled = true;
                document.getElementById('status').className = 'info';
                document.getElementById('status').textContent = 'Playback finished';
            }
        }
    }
});

// Add with other event listeners
document.getElementById('muteVideo').onchange = (event) => {
    video.muted = !event.target.checked;
};

// Add the event listener with others
document.getElementById('xOffset').oninput = (event) => {
    xOffset = parseInt(event.target.value);
    document.getElementById('xOffsetValue').textContent = xOffset;
    updateControls();
};

// Reset function to restore default values
function resetControls() {
    // Reset all values to defaults
    contrast = 1.0;
    brightness = 0;
    shadows = 0;
    midtones = 0;
    highlights = 0;
    redChannel = 1.0;
    greenChannel = 1.0;
    blueChannel = 1.0;
    xOffset = 0;

    // Reset all sliders and their displays
    document.getElementById('contrast').value = 100;
    document.getElementById('contrastValue').textContent = '1.0';

    document.getElementById('brightness').value = 0;
    document.getElementById('brightnessValue').textContent = '0';

    document.getElementById('shadows').value = 0;
    document.getElementById('shadowsValue').textContent = '0';

    document.getElementById('midtones').value = 0;
    document.getElementById('midtonesValue').textContent = '0';

    document.getElementById('highlights').value = 0;
    document.getElementById('highlightsValue').textContent = '0';

    document.getElementById('red').value = 100;
    document.getElementById('redValue').textContent = '100';

    document.getElementById('green').value = 100;
    document.getElementById('greenValue').textContent = '100';

    document.getElementById('blue').value = 100;
    document.getElementById('blueValue').textContent = '100';

    document.getElementById('xOffset').value = 0;
    document.getElementById('xOffsetValue').textContent = '0';

    // Update preview
    updateControls();
}

// Add the reset button event listener
document.getElementById('resetButton').onclick = resetControls;

// Add after the resetControls function
function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomizeControls() {
    // Randomize values within reasonable ranges
    contrast = (getRandomInt(50, 150) / 100);  // 0.5 to 1.5
    brightness = getRandomInt(-50, 50);        // -50 to 50
    shadows = getRandomInt(-50, 50);           // -50 to 50
    midtones = getRandomInt(-50, 50);          // -50 to 50
    highlights = getRandomInt(-50, 50);        // -50 to 50
    redChannel = (getRandomInt(50, 150) / 100);   // 0.5 to 1.5
    greenChannel = (getRandomInt(50, 150) / 100); // 0.5 to 1.5
    blueChannel = (getRandomInt(50, 150) / 100);  // 0.5 to 1.5
    xOffset = getRandomInt(-50, 50);           // -50 to 50

    // Update all sliders and their displays
    document.getElementById('contrast').value = contrast * 100;
    document.getElementById('contrastValue').textContent = contrast.toFixed(1);

    document.getElementById('brightness').value = brightness;
    document.getElementById('brightnessValue').textContent = brightness;

    document.getElementById('shadows').value = shadows;
    document.getElementById('shadowsValue').textContent = shadows;

    document.getElementById('midtones').value = midtones;
    document.getElementById('midtonesValue').textContent = midtones;

    document.getElementById('highlights').value = highlights;
    document.getElementById('highlightsValue').textContent = highlights;

    document.getElementById('red').value = redChannel * 100;
    document.getElementById('redValue').textContent = Math.round(redChannel * 100);

    document.getElementById('green').value = greenChannel * 100;
    document.getElementById('greenValue').textContent = Math.round(greenChannel * 100);

    document.getElementById('blue').value = blueChannel * 100;
    document.getElementById('blueValue').textContent = Math.round(blueChannel * 100);

    document.getElementById('xOffset').value = xOffset;
    document.getElementById('xOffsetValue').textContent = xOffset;

    // Update preview
    updateControls();
}

// Add the random button event listener
document.getElementById('randomButton').onclick = randomizeControls;
