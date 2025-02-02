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
let colorizeColor = '#4a90e2';
let colorizeAmount = 0;
let colorLevels = 256;  // Number of color levels per channel
let oneBitMode = false;
let primaryColor = '#ffffff';
let secondaryColor = '#000000';
let oneBitThreshold = 128;
let gaussianMid = 0.5;
let gaussianSpread = 0.25;
let gaussianStrength = 0.5;
let gaussianEnabled = false;
let invertEnabled = false;
let colorSwapEnabled = false;
let colorSwapSource = '#ff0000';
let colorSwapTarget = '#000000';
let colorSwapThreshold = 30;

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

// Define default values for all sliders
const DEFAULT_VALUES = {
    'contrast': 100,        // 1.0
    'brightness': 0,
    'shadows': 0,
    'midtones': 0,
    'highlights': 0,
    'red': 100,            // 100%
    'green': 100,          // 100%
    'blue': 100,           // 100%
    'xOffset': 0,
    'colorizeAmount': 0,
    'colorLevels': 256,
    'oneBitThreshold': 128,
    'gaussianMid': 50,     // 0.5
    'gaussianSpread': 25,  // 0.25
    'gaussianStrength': 50 // 0.5
};

// Add double-click handlers to all sliders
Object.keys(DEFAULT_VALUES).forEach(id => {
    const slider = document.getElementById(id);
    if (slider) {
        slider.addEventListener('dblclick', () => {
            slider.value = DEFAULT_VALUES[id];

            // Update the corresponding value display and variable
            switch (id) {
                case 'contrast':
                    contrast = DEFAULT_VALUES[id] / 100;
                    document.getElementById('contrastValue').textContent = contrast.toFixed(1);
                    break;
                case 'brightness':
                    brightness = DEFAULT_VALUES[id];
                    document.getElementById('brightnessValue').textContent = brightness;
                    break;
                case 'shadows':
                    shadows = DEFAULT_VALUES[id];
                    document.getElementById('shadowsValue').textContent = shadows;
                    break;
                case 'midtones':
                    midtones = DEFAULT_VALUES[id];
                    document.getElementById('midtonesValue').textContent = midtones;
                    break;
                case 'highlights':
                    highlights = DEFAULT_VALUES[id];
                    document.getElementById('highlightsValue').textContent = highlights;
                    break;
                case 'red':
                    redChannel = DEFAULT_VALUES[id] / 100;
                    document.getElementById('redValue').textContent = DEFAULT_VALUES[id];
                    break;
                case 'green':
                    greenChannel = DEFAULT_VALUES[id] / 100;
                    document.getElementById('greenValue').textContent = DEFAULT_VALUES[id];
                    break;
                case 'blue':
                    blueChannel = DEFAULT_VALUES[id] / 100;
                    document.getElementById('blueValue').textContent = DEFAULT_VALUES[id];
                    break;
                case 'xOffset':
                    xOffset = DEFAULT_VALUES[id];
                    document.getElementById('xOffsetValue').textContent = xOffset;
                    break;
                case 'colorizeAmount':
                    colorizeAmount = DEFAULT_VALUES[id];
                    document.getElementById('colorizeAmountValue').textContent = colorizeAmount;
                    break;
                case 'colorLevels':
                    colorLevels = DEFAULT_VALUES[id];
                    document.getElementById('colorLevelsValue').textContent = colorLevels;
                    break;
                case 'oneBitThreshold':
                    oneBitThreshold = DEFAULT_VALUES[id];
                    document.getElementById('oneBitThresholdValue').textContent = oneBitThreshold;
                    break;
                case 'gaussianMid':
                    gaussianMid = DEFAULT_VALUES[id] / 100;
                    document.getElementById('gaussianMidValue').textContent = gaussianMid.toFixed(2);
                    break;
                case 'gaussianSpread':
                    gaussianSpread = DEFAULT_VALUES[id] / 100;
                    document.getElementById('gaussianSpreadValue').textContent = gaussianSpread.toFixed(2);
                    break;
                case 'gaussianStrength':
                    gaussianStrength = DEFAULT_VALUES[id] / 100;
                    document.getElementById('gaussianStrengthValue').textContent = gaussianStrength.toFixed(2);
                    break;
            }
            updateControls();
        });
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

// Add this helper function at the top with other utility functions
function hexToRgb(hex) {
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    return [r, g, b];
}

// Add this helper function for color blending
function blendColorize(original, targetRGB, intensity, channel) {
    // Get luminance of original pixel
    const luminance = original / 255;

    // Get target color for this channel
    const targetValue = channel === redChannel ? targetRGB[0] :
        channel === greenChannel ? targetRGB[1] : targetRGB[2];

    // Overlay blend mode formula
    let result;
    if (luminance < 0.5) {
        result = (2 * original * targetValue) / 255;
    } else {
        result = 255 - (2 * (255 - original) * (255 - targetValue)) / 255;
    }

    // Blend between original and overlaid color
    return original * (1 - intensity) + result * intensity;
}

// Add this shared processing function
function processFrame(sourceCanvas, sourceCtx) {
    const imageData = sourceCtx.getImageData(0, 0, PANEL_WIDTH, PANEL_HEIGHT);
    const data = imageData.data;
    const rgbData = new Uint8Array(PANEL_WIDTH * PANEL_HEIGHT * 3);
    let rgbIndex = 0;

    for (let i = 0; i < data.length; i += 4) {
        // Get RGB values
        let rr = adjustPixel(data[i], contrast, brightness, redChannel);     // R
        let gg = adjustPixel(data[i + 1], contrast, brightness, greenChannel); // G
        let bb = adjustPixel(data[i + 2], contrast, brightness, blueChannel);  // B

        // Apply colorize effect after other adjustments
        if (colorizeAmount > 0) {
            const targetRGB = hexToRgb(colorizeColor);
            const intensity = colorizeAmount / 100;
            rr = blendColorize(rr, targetRGB, intensity, redChannel);
            gg = blendColorize(gg, targetRGB, intensity, greenChannel);
            bb = blendColorize(bb, targetRGB, intensity, blueChannel);
        }

        // Apply color reduction
        if (colorLevels < 256) {
            rr = reduceColors(rr);
            gg = reduceColors(gg);
            bb = reduceColors(bb);
        }

        // Apply 1-bit mode
        if (oneBitMode) {
            const luminance = (rr * 0.299 + gg * 0.587 + bb * 0.114);
            const primary = hexToRgb(primaryColor);
            const secondary = hexToRgb(secondaryColor);
            if (luminance >= oneBitThreshold) {
                rr = primary[0];
                gg = primary[1];
                bb = primary[2];
            } else {
                rr = secondary[0];
                gg = secondary[1];
                bb = secondary[2];
            }
        }

        // Apply invert effect
        if (invertEnabled) {
            rr = 255 - rr;
            gg = 255 - gg;
            bb = 255 - bb;
        }

        // Apply color swap effect
        if (colorSwapEnabled) {
            const sourceRGB = hexToRgb(colorSwapSource);
            const targetRGB = hexToRgb(colorSwapTarget);

            const colorDistance = Math.sqrt(
                Math.pow(rr - sourceRGB[0], 2) +
                Math.pow(gg - sourceRGB[1], 2) +
                Math.pow(bb - sourceRGB[2], 2)
            );

            if (colorDistance <= colorSwapThreshold) {
                rr = targetRGB[0];
                gg = targetRGB[1];
                bb = targetRGB[2];
            }
        }

        // Store adjusted values
        data[i] = Math.max(0, Math.min(255, rr));
        data[i + 1] = Math.max(0, Math.min(255, gg));
        data[i + 2] = Math.max(0, Math.min(255, bb));

        // Store RGB values for binary output
        rgbData[rgbIndex++] = data[i];
        rgbData[rgbIndex++] = data[i + 1];
        rgbData[rgbIndex++] = data[i + 2];
    }

    sourceCtx.putImageData(imageData, 0, 0);
    return rgbData;
}

// Update the preview function to use the shared processor
function updatePreview() {
    if (video.readyState < 2 || isStreaming) {
        requestAnimationFrame(updatePreview);
        return;
    }

    const crop = calculateCrop(video.videoWidth, video.videoHeight);

    // Draw at panel resolution with crop
    previewCtx.drawImage(video,
        crop.sourceX, crop.sourceY, crop.sourceWidth, crop.sourceHeight,
        0, 0, PANEL_WIDTH, PANEL_HEIGHT
    );

    // Process the frame
    processFrame(previewCanvas, previewCtx);

    requestAnimationFrame(updatePreview);
}

// Update the convertToBin function to use the same processor
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
            video.currentTime = i / TARGET_FPS;

            // Wait for the video to seek
            await new Promise(resolve => {
                video.onseeked = resolve;
            });

            const crop = calculateCrop(video.videoWidth, video.videoHeight);

            // Draw with crop
            ctx.drawImage(video,
                crop.sourceX, crop.sourceY, crop.sourceWidth, crop.sourceHeight,
                0, 0, PANEL_WIDTH, PANEL_HEIGHT
            );

            // Process the frame using the same function as preview
            const rgbData = processFrame(canvas, ctx);

            // Add to binary buffer
            binData.set(rgbData, binOffset);
            binOffset += rgbData.length;

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

// Add the streamVideo function
async function streamVideo() {
    if (!port || !video.src) return;

    const writer = port.writable.getWriter();
    let lastFrameTime = performance.now();
    frameCount = 0;
    lastFpsTime = performance.now();

    try {
        while (isStreaming) {
            const currentTime = performance.now();
            const elapsed = currentTime - lastFrameTime;

            if (elapsed >= FRAME_TIME) {
                // Process frame using our shared function
                const crop = calculateCrop(video.videoWidth, video.videoHeight);

                // Draw with crop
                ctx.drawImage(video,
                    crop.sourceX, crop.sourceY, crop.sourceWidth, crop.sourceHeight,
                    0, 0, PANEL_WIDTH, PANEL_HEIGHT
                );

                // Process the frame using shared processor
                const rgbData = processFrame(canvas, ctx);

                // Send frame in chunks
                for (let i = 0; i < rgbData.length; i += CHUNK_SIZE) {
                    const chunk = rgbData.slice(i, i + CHUNK_SIZE);
                    await writer.write(chunk);
                }

                frameCount++;
                if (currentTime - lastFpsTime >= 1000) {
                    const fps = frameCount;
                    document.getElementById('fps').textContent = `FPS: ${fps}`;
                    frameCount = 0;
                    lastFpsTime = currentTime;
                }

                lastFrameTime = currentTime;

                // Check if we need to loop
                if (video.ended) {
                    if (shouldLoop) {
                        video.currentTime = trimStart;
                        video.play();
                    } else {
                        isStreaming = false;
                        break;
                    }
                }
            }

            // Wait for next frame
            await new Promise(resolve => setTimeout(resolve, 1));
        }
    } catch (error) {
        console.error('Stream error:', error);
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Streaming error: ' + error.message;
    } finally {
        writer.releaseLock();
        if (!shouldLoop || !isStreaming) {
            video.pause();
            document.getElementById('streamButton').disabled = false;
            document.getElementById('stopButton').disabled = true;
            document.getElementById('status').className = 'info';
            document.getElementById('status').textContent = 'Stream ended';
        }
    }
}

// Add the stream button click handler
document.getElementById('streamButton').onclick = () => {
    if (!port || !video.src) return;

    isStreaming = true;
    video.currentTime = trimStart;
    video.play();

    document.getElementById('streamButton').disabled = true;
    document.getElementById('stopButton').disabled = false;
    document.getElementById('status').className = 'info';
    document.getElementById('status').textContent = 'Streaming video...';
    streamVideo();
};

// Add the stop button click handler
document.getElementById('stopButton').onclick = () => {
    isStreaming = false;
    video.pause();
    document.getElementById('streamButton').disabled = false;
    document.getElementById('stopButton').disabled = true;
    document.getElementById('status').className = 'info';
    document.getElementById('status').textContent = 'Stream stopped';
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

// Modify the updateControls function with the new processFrame function
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
    colorizeAmount = 0;
    colorLevels = 256;
    oneBitMode = false;
    document.getElementById('oneBitMode').checked = false;
    document.getElementById('primaryColor').value = '#ffffff';
    document.getElementById('secondaryColor').value = '#000000';
    document.getElementById('oneBitThreshold').value = 128;
    document.getElementById('oneBitThresholdValue').textContent = '128';
    primaryColor = '#ffffff';
    secondaryColor = '#000000';
    oneBitThreshold = 128;
    document.querySelector('.one-bit-control').classList.remove('active');
    gaussianMid = 0.5;
    gaussianSpread = 0.25;
    gaussianStrength = 0.5;
    document.getElementById('gaussianMid').value = 50;
    document.getElementById('gaussianSpread').value = 25;
    document.getElementById('gaussianStrength').value = 50;
    document.getElementById('gaussianMidValue').textContent = '0.5';
    document.getElementById('gaussianSpreadValue').textContent = '0.25';
    document.getElementById('gaussianStrengthValue').textContent = '0.5';
    gaussianEnabled = false;
    document.getElementById('gaussianEnabled').checked = false;
    document.querySelector('.gaussian-sliders').classList.remove('active');
    invertEnabled = false;
    document.getElementById('invertEnabled').checked = false;
    colorSwapEnabled = false;
    document.getElementById('colorSwapEnabled').checked = false;
    document.getElementById('colorSwapSource').value = '#ff0000';
    document.getElementById('colorSwapTarget').value = '#000000';
    document.getElementById('colorSwapThreshold').value = 30;
    document.getElementById('colorSwapThresholdValue').textContent = '30';
    document.querySelector('.color-swap-control').classList.remove('active');
    colorSwapSource = '#ff0000';
    colorSwapTarget = '#000000';
    colorSwapThreshold = 30;

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

    document.getElementById('colorizeAmount').value = 0;
    document.getElementById('colorizeAmountValue').textContent = '0';
    document.getElementById('colorizeColor').value = '#4a90e2';
    colorizeColor = '#4a90e2';

    document.getElementById('colorLevels').value = 256;
    document.getElementById('colorLevelsValue').textContent = '256';

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
    colorizeAmount = getRandomInt(0, 100);
    colorLevels = Math.pow(2, getRandomInt(2, 8)); // 4 to 256 colors in power of 2 steps
    oneBitMode = Math.random() < 0.5;
    document.getElementById('oneBitMode').checked = oneBitMode;
    document.querySelector('.one-bit-control').classList.toggle('active', oneBitMode);

    // Random colors
    primaryColor = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    secondaryColor = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    document.getElementById('primaryColor').value = primaryColor;
    document.getElementById('secondaryColor').value = secondaryColor;

    oneBitThreshold = getRandomInt(64, 192);
    document.getElementById('oneBitThreshold').value = oneBitThreshold;
    document.getElementById('oneBitThresholdValue').textContent = oneBitThreshold;

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

    document.getElementById('colorizeAmount').value = colorizeAmount;
    document.getElementById('colorizeAmountValue').textContent = colorizeAmount;

    // Random color
    const randomColor = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    document.getElementById('colorizeColor').value = randomColor;
    colorizeColor = randomColor;

    document.getElementById('colorLevels').value = colorLevels;
    document.getElementById('colorLevelsValue').textContent = colorLevels;

    // Random Gaussian values
    gaussianMid = getRandomInt(30, 70) / 100;
    gaussianSpread = getRandomInt(10, 40) / 100;
    gaussianStrength = getRandomInt(20, 80) / 100;
    document.getElementById('gaussianMid').value = gaussianMid * 100;
    document.getElementById('gaussianSpread').value = gaussianSpread * 100;
    document.getElementById('gaussianStrength').value = gaussianStrength * 100;
    document.getElementById('gaussianMidValue').textContent = gaussianMid.toFixed(2);
    document.getElementById('gaussianSpreadValue').textContent = gaussianSpread.toFixed(2);
    document.getElementById('gaussianStrengthValue').textContent = gaussianStrength.toFixed(2);

    // Update preview
    updateControls();

    gaussianEnabled = Math.random() < 0.5;
    document.getElementById('gaussianEnabled').checked = gaussianEnabled;
    document.querySelector('.gaussian-sliders').classList.toggle('active', gaussianEnabled);
    invertEnabled = Math.random() < 0.5;
    document.getElementById('invertEnabled').checked = invertEnabled;
    colorSwapEnabled = Math.random() < 0.5;
    document.getElementById('colorSwapEnabled').checked = colorSwapEnabled;
    document.querySelector('.color-swap-control').classList.toggle('active', colorSwapEnabled);

    // Random colors for swap
    const randomSource = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    const randomTarget = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
    document.getElementById('colorSwapSource').value = randomSource;
    document.getElementById('colorSwapTarget').value = randomTarget;
    colorSwapSource = randomSource;
    colorSwapTarget = randomTarget;

    colorSwapThreshold = getRandomInt(10, 50);
    document.getElementById('colorSwapThreshold').value = colorSwapThreshold;
    document.getElementById('colorSwapThresholdValue').textContent = colorSwapThreshold;
}

// Add the random button event listener
document.getElementById('randomButton').onclick = randomizeControls;

// Add the colorize event listeners
document.getElementById('colorizeColor').onchange = (event) => {
    colorizeColor = event.target.value;
    updateControls();
};

document.getElementById('colorizeAmount').oninput = (event) => {
    colorizeAmount = parseInt(event.target.value);
    document.getElementById('colorizeAmountValue').textContent = colorizeAmount;
    updateControls();
};

// Add the color levels event listener
document.getElementById('colorLevels').oninput = (event) => {
    colorLevels = parseInt(event.target.value);
    document.getElementById('colorLevelsValue').textContent = colorLevels;
    updateControls();
};

// Add color reduction function
function reduceColors(value) {
    if (colorLevels === 256) return value;

    // Calculate step size for the given number of levels
    const step = 256 / (colorLevels - 1);

    // Quantize the value to nearest step
    return Math.round(Math.round(value / step) * step);
}

// Add event listeners
document.getElementById('oneBitMode').onchange = (event) => {
    oneBitMode = event.target.checked;
    document.querySelector('.one-bit-control').classList.toggle('active', oneBitMode);
    updateControls();
};

document.getElementById('primaryColor').onchange = (event) => {
    primaryColor = event.target.value;
    updateControls();
};

document.getElementById('secondaryColor').onchange = (event) => {
    secondaryColor = event.target.value;
    updateControls();
};

document.getElementById('oneBitThreshold').oninput = (event) => {
    oneBitThreshold = parseInt(event.target.value);
    document.getElementById('oneBitThresholdValue').textContent = oneBitThreshold;
    updateControls();
};

// Update the format time function to show seconds with one decimal
function formatTime(seconds) {
    return seconds.toFixed(1) + 's';
}

// Add these event listeners
video.addEventListener('loadedmetadata', () => {
    document.getElementById('totalTime').textContent = formatTime(video.duration);
});

video.addEventListener('timeupdate', () => {
    document.getElementById('currentTime').textContent = formatTime(video.currentTime);
});

// Add event listeners
document.getElementById('gaussianMid').oninput = (event) => {
    gaussianMid = event.target.value / 100;
    document.getElementById('gaussianMidValue').textContent = gaussianMid.toFixed(2);
    updateControls();
};

document.getElementById('gaussianSpread').oninput = (event) => {
    gaussianSpread = event.target.value / 100;
    document.getElementById('gaussianSpreadValue').textContent = gaussianSpread.toFixed(2);
    updateControls();
};

document.getElementById('gaussianStrength').oninput = (event) => {
    gaussianStrength = event.target.value / 100;
    document.getElementById('gaussianStrengthValue').textContent = gaussianStrength.toFixed(2);
    updateControls();
};

// Update the event listener for the toggle
document.getElementById('gaussianEnabled').onchange = (event) => {
    gaussianEnabled = event.target.checked;
    document.querySelector('.gaussian-sliders').classList.toggle('active', gaussianEnabled);
    updateControls();
};

// Add event listener for invert checkbox
document.getElementById('invertEnabled').onchange = (event) => {
    invertEnabled = event.target.checked;
    updateControls();
};

// Add event listeners
document.getElementById('colorSwapEnabled').onchange = (event) => {
    colorSwapEnabled = event.target.checked;
    document.querySelector('.color-swap-control').classList.toggle('active', colorSwapEnabled);
    updateControls();
};

document.getElementById('colorSwapSource').onchange = (event) => {
    colorSwapSource = event.target.value;
    updateControls();
};

document.getElementById('colorSwapTarget').onchange = (event) => {
    colorSwapTarget = event.target.value;
    updateControls();
};

document.getElementById('colorSwapThreshold').oninput = (event) => {
    colorSwapThreshold = parseInt(event.target.value);
    document.getElementById('colorSwapThresholdValue').textContent = colorSwapThreshold;
    updateControls();
};

// Add this function back near the top with other utility functions
function calculateCrop(videoWidth, videoHeight) {
    const videoAspect = videoWidth / videoHeight;
    const panelAspect = PANEL_WIDTH / PANEL_HEIGHT;

    let sourceWidth, sourceHeight, sourceX, sourceY;

    if (videoAspect > panelAspect) {
        // Video is wider than panel
        sourceHeight = videoHeight;
        sourceWidth = videoHeight * panelAspect;
        sourceY = 0;
        sourceX = ((videoWidth - sourceWidth) / 2) + (xOffset / 100 * (videoWidth - sourceWidth));
    } else {
        // Video is taller than panel
        sourceWidth = videoWidth;
        sourceHeight = videoWidth / panelAspect;
        sourceX = 0;
        sourceY = (videoHeight - sourceHeight) / 2;
    }

    return {
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight
    };
}

// Also add back the adjustPixel function that was lost
function adjustPixel(value, contrast, brightness, channel) {
    // Apply contrast
    let newValue = ((value / 255 - 0.5) * contrast + 0.5) * 255;

    // Apply brightness
    newValue += brightness;

    // Apply Gaussian curve adjustment only if enabled
    if (gaussianEnabled) {
        const gaussianValue = newValue / 255;
        const gaussianAdjustment = Math.exp(
            -Math.pow(gaussianValue - gaussianMid, 2) / (2 * Math.pow(gaussianSpread, 2))
        );
        newValue = newValue * (1 + gaussianStrength * gaussianAdjustment);
    }

    // Apply tone adjustments
    const normalizedValue = newValue / 255;

    // Shadows affect dark areas (0-0.33)
    if (normalizedValue <= 0.33) {
        newValue += shadows * (1 - normalizedValue * 3);
    }

    // Midtones affect middle areas (0.33-0.66)
    if (normalizedValue > 0.33 && normalizedValue <= 0.66) {
        const midtoneFactor = (normalizedValue - 0.33) * 3;
        newValue += midtones * (1 - Math.abs(midtoneFactor - 0.5) * 2);
    }

    // Highlights affect bright areas (0.66-1.0)
    if (normalizedValue > 0.66) {
        newValue += highlights * ((normalizedValue - 0.66) * 3);
    }

    // Apply channel multiplier
    newValue *= channel;

    return newValue;
}
