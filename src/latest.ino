#include <OctoWS2811.h>
#include <SD.h>
#include <SPI.h>
#include <math.h>
#include <FastLED.h> // Add this at the top of the file

// latest dev version that has video and image layers, HSC for image and video and video looping and layer order and image video blending 7.9.24
// gamma correction removed and added HSV to led blocks
// X,Y shift for video and image layers
// we have 12 panels but there are always 2 pairs connected together. So 1 OctoWS2811 rj45 connector has 2 panels together, making it total 512 leds per OctoWS2811 channel.
// panels are stacked on top of each other in a grid of w32 x h96
// 2 panels are connected together so that the starting index is always left top right corner.
// updates at 5.10.24, 32,96 led panel support, disabled x,y off set via CC
// update 6.10.24, added vertical midi note mapping and fixed the issue when Blue,Red,Green blocks were not independent
// fix MIDI XY CC and reenable it to images
// 15.12.24, added support for 40x96 panel
// 15.12.24 add midi channel 5 for row light up
// 16.12.24 add midi channel 6 for strobe
// 16.12.24 fix constants and variables
// panels are stacked vertically, with the first panel being the top left, and the last panel being the bottom right.
// the panels are wired in a serpentine pattern, with the first panel being the top left, and the last panel being the bottom right.
// |c-1|c-2|c-3|c-4|c-5|
// |---|---|---|---|---|
// |1.1|3.2|4.1|6.2|7.1|
// |1.2|3.1|4.2|6.1|7.2|
// |2.1|2.2|5.1|5.2|8.1|

// Panel and LED configuration
const int NUM_PANELS = 8;
const int LEDS_PER_PANEL = 512;
const int GROUPS_PER_PANEL = 8;
const int PANEL_WIDTH = 8;       // Width of a single panel in pixels
const int PANEL_HEIGHT = 32;     // Height of a single panel in pixels
const int NUM_COLUMNS = 5;       // Number of panels horizontally
const int NUM_ROWS = 3;          // Number of panels vertically

// Display dimensions
const int width = 40;            // Total width (5 panels × 8 pixels)
const int height = 96;           // Total height (3 panels × 32 pixels)

// Derived constants
const int totalLeds = 3840;      // Total number of LEDs (40 × 96)
const int ledsPerGroup = LEDS_PER_PANEL / GROUPS_PER_PANEL;
const int numGroups = NUM_PANELS * GROUPS_PER_PANEL;
const int totalNotes = numGroups * 3;  // Total notes for all colors (blue, red, green)

// MIDI channel assignments
const int LED_MIDI_CHANNEL_LEFT = 1;
const int LED_MIDI_CHANNEL_RIGHT = 2;
const int VIDEO_MIDI_CHANNEL = 3;
const int IMAGE_MIDI_CHANNEL = 4;
const int ROW_MIDI_CHANNEL = 5;
const int STROBE_MIDI_CHANNEL = 6;

// Row and block configuration
const int ROWS_PER_PANEL = 32;
const int TOTAL_ROWS = 96;       // Total height of the display
const int BLOCKS_PER_PANEL = 4;  // Each panel has 4 blocks of 64 LEDs
const int BLOCKS_PER_COLUMN = 12;  // 3 panels × 4 blocks = 12 blocks per column

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

struct GroupState
{
    uint8_t blue;
    uint8_t red;
    uint8_t green;
};

GroupState groupStates[numGroups] = {0};
bool ledStateChanged = false;

byte frameBuffer[totalLeds * 3];
byte imageBuffer[totalLeds * 3];
bool videoPlaying = false;
bool imageLayerActive = false;

// Brightness threshold (0-255)
const int brightnessThreshold = 5;

// SD card chip select pin
const int chipSelect = BUILTIN_SDCARD;

// Video playback variables
File mediaFile;
bool imageDisplayed = false;
unsigned long lastFrameTime = 0;
const unsigned long frameDelay = 33; // ~30 fps

const int MAX_MAPPINGS = 20; // Maximum number of video/image mappings

struct Mapping
{
    byte note;
    char filename[13];  // 8.3 filename format + null terminator
    uint8_t brightness; // Add brightness to the Mapping struct
};

Mapping videoMappings[MAX_MAPPINGS];
Mapping imageMappings[MAX_MAPPINGS];
int numVideos = 0;
int numImages = 0;

// Gamma correction table
const float gammaValue = 2.2;
uint8_t gammaTable[256];

char currentImageFilename[13] = {0}; // To store the current image filename

const int HUE_CC = 1;
const int SATURATION_CC = 2;
const int VALUE_CC = 3;
const int X_POSITION_CC = 4;
const int Y_POSITION_CC = 5;

struct HSVAdjustments
{
    uint8_t hue;
    uint8_t saturation;
    uint8_t value;
};

HSVAdjustments videoAdjustments = {0, 255, 255};    // Default to no adjustment
HSVAdjustments imageAdjustments = {0, 255, 255};    // Default to no adjustment
HSVAdjustments ledBlockAdjustments = {0, 255, 255}; // Default to no adjustment

bool videoLooping = false;
unsigned long videoStartPosition = 0;
unsigned long videoFileSize = 0;

int imageOffsetX = 0;
int imageOffsetY = 0;
int videoOffsetX = 0;
int videoOffsetY = 0;

bool strobeActive[totalLeds] = {false};  // Track which LEDs are controlled by strobe

bool activeVideoNotes[128] = {false};  // Track which video notes are currently active

unsigned long lastVideoFrame = 0;  // Track when we last processed a video frame
bool videoNeedsUpdate = false;     // Flag to indicate if video needs updating

int mapCCToOffset(int value, int maxOffset)
{
    // Ensure the full range of movement, including off-screen, while keeping 64 centered
    if (value == 64)
        return 0; // Ensure exact center at 64
    else if (value < 64)
    {
        return map(value, 0, 63, -maxOffset, -1);
    }
    else
    {
        return map(value, 65, 127, 1, maxOffset);
    }
}

void createGammaTable()
{
    for (int i = 0; i < 256; i++)
    {
        gammaTable[i] = (uint8_t)(pow((float)i / 255.0, gammaValue) * 255.0 + 0.5);
    }
}

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
    return map(velocity, 0, 127, 0, 255);
}

int mapXYtoLedIndex(int x, int y) {
    // Determine which panel we're in
    int panel_column = x / PANEL_WIDTH;
    int panel_row = y / PANEL_HEIGHT;

    // Get coordinates within the panel
    int x_in_panel = x % PANEL_WIDTH;
    int y_in_panel = y % PANEL_HEIGHT;

    // Calculate panel index based on wiring sequence
    int panel_index;
    if (panel_column % 2 == 0) {
        // Even columns: panels connected top to bottom
        panel_index = panel_column * NUM_ROWS + panel_row;
    } else {
        // Odd columns: panels connected bottom to top
        panel_index = panel_column * NUM_ROWS + (NUM_ROWS - 1 - panel_row);
    }

    // Calculate LED index within panel (serpentine pattern)
    int led_in_panel;
    if (panel_column % 2 == 0) {
        // Normal panel orientation
        if (y_in_panel % 2 == 0) {
            // Even rows go right to left
            led_in_panel = y_in_panel * PANEL_WIDTH + (PANEL_WIDTH - 1 - x_in_panel);
        } else {
            // Odd rows go left to right
            led_in_panel = y_in_panel * PANEL_WIDTH + x_in_panel;
        }
    } else {
        // Reversed panel orientation
        int y_reversed = (PANEL_HEIGHT - 1) - y_in_panel;
        if (y_reversed % 2 == 0) {
            // Even rows in reversed panel
            led_in_panel = y_reversed * PANEL_WIDTH + x_in_panel;
        } else {
            // Odd rows in reversed panel
            led_in_panel = y_reversed * PANEL_WIDTH + (PANEL_WIDTH - 1 - x_in_panel);
        }
    }

    // Calculate final LED index
    return panel_index * (PANEL_WIDTH * PANEL_HEIGHT) + led_in_panel;
}

void handleLEDNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if ((channel != LED_MIDI_CHANNEL_LEFT && channel != LED_MIDI_CHANNEL_RIGHT) || pitch > 127)
        return;

    int noteIndex = 127 - pitch;  // Convert MIDI note to zero-based index

    // Each column has 3 colors × 12 blocks = 36 notes
    const int NOTES_PER_COLOR = BLOCKS_PER_COLUMN;  // 12 blocks
    const int NOTES_PER_COLUMN = NOTES_PER_COLOR * 3;  // 36 notes per column (12 blue + 12 red + 12 green)

    // Calculate which column and color we're targeting
    int column;
    if (channel == LED_MIDI_CHANNEL_LEFT) {
        column = noteIndex / NOTES_PER_COLUMN;
        if (column > 2) return;  // Only handle first 3 columns on channel 1
    } else {
        column = 3 + (noteIndex / NOTES_PER_COLUMN);  // Start from column 4 for channel 2
        if (column > 4) return;  // Only handle columns 4-5 on channel 2
    }

    int remaining = noteIndex % NOTES_PER_COLUMN;

    // Determine which color (0=blue, 1=red, 2=green) and position within color section
    int colorSection = remaining / NOTES_PER_COLOR;
    int blockInColumn = remaining % NOTES_PER_COLOR;  // 0-11 for position within column

    // Calculate which panel in the column (0-2) and which block in the panel (0-3)
    int panelInColumn = blockInColumn / BLOCKS_PER_PANEL;  // 0-2 for panel position
    int blockInPanel = blockInColumn % BLOCKS_PER_PANEL;   // 0-3 for block in panel

    // Panel mapping based on the serpentine pattern
    // Column 1: 1.1 → 1.2 → 2.1
    // Column 2: 3.2 → 3.1 → 2.2
    // Column 3: 4.1 → 4.2 → 5.1
    // Column 4: 6.2 → 6.1 → 5.2
    // Column 5: 7.1 → 7.2 → 8.1
    if (column % 2 == 1) {  // Odd columns (c-2, c-4)
        // Start from top, but panels are numbered from bottom
        panelInColumn = 2 - panelInColumn;
        // Reverse block order within panel
        blockInPanel = BLOCKS_PER_PANEL - 1 - blockInPanel;
    }

    // Calculate final panel index and group index
    int panel_index = column * NUM_ROWS + panelInColumn;
    int groupIndex = (panel_index * BLOCKS_PER_PANEL) + blockInPanel;

    // Set the color based on velocity
    uint8_t brightness = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    // Get the LED index range for this group
    int startLed = groupIndex * ledsPerGroup;
    int endLed = startLed + ledsPerGroup;

    // Only update if LED is not controlled by strobe
    for (int i = startLed; i < endLed; i++) {
        if (!strobeActive[i]) {
            // Update the appropriate color based on the color section
            // Now we only update the specific color component without affecting others
            switch (colorSection) {
                case 0:  // Blue section
                    groupStates[groupIndex].blue = brightness;
                    break;
                case 1:  // Red section
                    groupStates[groupIndex].red = brightness;
                    break;
                case 2:  // Green section
                    groupStates[groupIndex].green = brightness;
                    break;
            }
        }
    }

    updateLEDs();
}

void handleRowNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != ROW_MIDI_CHANNEL || pitch > 127)
        return;

    // Direct mapping: note 127->row 0 (first 8 LEDs), 126->row 1 (next 8 LEDs), etc.
    int noteIndex = 127 - pitch;  // Convert MIDI note to row number

    // We have 12 rows total, so each color gets 12 notes
    const int ROWS_PER_COLOR = 12;

    // Calculate which color section we're in (0=Blue, 1=Red, 2=Green)
    int colorSection = noteIndex / ROWS_PER_COLOR;  // Switch color every 12 notes
    int rowIndex = noteIndex % ROWS_PER_COLOR;      // Row within current color section

    if (colorSection >= 3) return;  // Ignore notes beyond our 3 colors

    // Convert row number to LED Y position (each row is 8 LEDs high)
    rowIndex = rowIndex * 8;

    // Set the color based on velocity
    uint8_t brightness = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    // Light up the entire row (8 LEDs high)
    for (int x = 0; x < width; x++) {
        for (int y = rowIndex; y < rowIndex + 8; y++) {
            int ledIndex = mapXYtoLedIndex(x, y);
            // Only update if LED is not controlled by strobe
            if (!strobeActive[ledIndex]) {
                int group = ledIndex / ledsPerGroup;
                switch (colorSection) {
                    case 0:  // Blue section
                        groupStates[group].blue = brightness;
                        break;
                    case 1:  // Red section
                        groupStates[group].red = brightness;
                        break;
                    case 2:  // Green section
                        groupStates[group].green = brightness;
                        break;
                }
            }
        }
    }

    updateLEDs();
}

void loadMappings(const char *filename, Mapping *mappings, int &count)
{
    File mapFile = SD.open(filename, FILE_READ);
    if (!mapFile)
    {
        Serial.print("Failed to open ");
        Serial.println(filename);
        return;
    }

    count = 0;
    while (mapFile.available() && count < MAX_MAPPINGS)
    {
        String line = mapFile.readStringUntil('\n');
        line.trim();
        int commaIndex = line.indexOf(',');
        if (commaIndex > 0)
        {
            mappings[count].note = line.substring(0, commaIndex).toInt();
            line.substring(commaIndex + 1).toCharArray(mappings[count].filename, 13);
            count++;
        }
    }

    mapFile.close();
    Serial.print("Loaded ");
    Serial.print(count);
    Serial.print(" mappings from ");
    Serial.println(filename);
}

void handleVideoNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != VIDEO_MIDI_CHANNEL)
        return;

    if (isNoteOn)
    {
        activeVideoNotes[pitch] = true;  // Mark this note as active
        for (int i = 0; i < numVideos; i++)
        {
            if (videoMappings[i].note == pitch)
            {
                startVideo(videoMappings[i].filename);
                return;
            }
        }
    }
    else
    {
        activeVideoNotes[pitch] = false;  // Mark this note as inactive
        videoNeedsUpdate = true;  // Flag that we need to check video state
    }
}

void handleImageNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != IMAGE_MIDI_CHANNEL)
        return;

    if (isNoteOn)
    {
        for (int i = 0; i < numImages; i++)
        {
            if (imageMappings[i].note == pitch)
            {
                imageMappings[i].brightness = mapVelocityToBrightness(velocity); // Set brightness based on velocity
                startImage(imageMappings[i].filename);
                return;
            }
        }
    }
    else
    {
        stopImage();
    }
}

void handleControlChange(byte channel, byte control, byte value)
{
    HSVAdjustments *adjustments = nullptr;

    if (channel == LED_MIDI_CHANNEL_LEFT || channel == LED_MIDI_CHANNEL_RIGHT)
    {
        adjustments = &ledBlockAdjustments;
    }
    else if (channel == VIDEO_MIDI_CHANNEL)
    {
        adjustments = &videoAdjustments;
    }
    else if (channel == IMAGE_MIDI_CHANNEL)
    {
        adjustments = &imageAdjustments;
    }

    if (adjustments)
    {
        switch (control)
        {
        case HUE_CC:
            adjustments->hue = value * 2; // Scale 0-127 to 0-254
            break;
        case SATURATION_CC:
            adjustments->saturation = map(value, 0, 127, 0, 255);
            break;
        case VALUE_CC:
            adjustments->value = map(value, 0, 127, 0, 255);
            break;
        case X_POSITION_CC:
            if (channel == VIDEO_MIDI_CHANNEL)
            {
                videoOffsetX = mapCCToOffset(value, width);
            }
            else if (channel == IMAGE_MIDI_CHANNEL)
            {
                imageOffsetX = mapCCToOffset(value, width);
            }
            break;
        case Y_POSITION_CC:
            if (channel == VIDEO_MIDI_CHANNEL)
            {
                videoOffsetY = mapCCToOffset(value, height);
            }
            else if (channel == IMAGE_MIDI_CHANNEL)
            {
                imageOffsetY = mapCCToOffset(value, height);
            }
            break;
        }
        updateLEDs();
    }
}

void startVideo(const char *filename)
{
    if (videoPlaying)
    {
        mediaFile.close();
    }
    mediaFile = SD.open(filename, FILE_READ);
    if (mediaFile)
    {
        videoPlaying = true;
        videoLooping = true;
        lastFrameTime = millis();
        videoStartPosition = mediaFile.position();
        videoFileSize = mediaFile.size();
        Serial.print("Started video: ");
        Serial.println(filename);
    }
    else
    {
        Serial.print("Failed to open video file: ");
        Serial.println(filename);
    }
}

void stopVideo()
{
    videoPlaying = false;
    videoLooping = false;
    mediaFile.close();
    memset(frameBuffer, 0, sizeof(frameBuffer));
    updateLEDs();
    Serial.println("Stopped video");
}

void startImage(const char *filename)
{
    File imageFile = SD.open(filename, FILE_READ);
    if (imageFile)
    {
        imageFile.read(imageBuffer, totalLeds * 3);
        imageFile.close();
        imageLayerActive = true;
        strncpy(currentImageFilename, filename, 12); // Copy at most 12 characters
        currentImageFilename[12] = '\0';             // Ensure null-termination
        Serial.print("Started image: ");
        Serial.println(filename);
        updateLEDs();
    }
    else
    {
        Serial.print("Failed to open image file: ");
        Serial.println(filename);
    }
}

void stopImage()
{
    imageLayerActive = false;
    memset(imageBuffer, 0, sizeof(imageBuffer));
    updateLEDs();
    Serial.println("Stopped image");
}

void updateLEDs()
{
    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
        {
            int ledIndex = mapXYtoLedIndex(x, y);
            int group = ledIndex / ledsPerGroup;

            // If this LED is controlled by strobe, use strobe values directly
            if (strobeActive[ledIndex]) {
                leds.setPixel(ledIndex,
                    groupStates[group].red,
                    groupStates[group].green,
                    groupStates[group].blue);
                continue;  // Skip all other processing for this LED
            }

            int r = 0, g = 0, b = 0;

            // Check if strobe is active for this LED
            // Strobe is when all RGB values are equal and non-zero
            if (groupStates[group].red > 0 &&
                groupStates[group].red == groupStates[group].green &&
                groupStates[group].red == groupStates[group].blue)
            {
                // Use strobe values directly, no blending or modifications allowed
                r = groupStates[group].red;
                g = groupStates[group].green;
                b = groupStates[group].blue;
            }
            else
            {
                // Clear any residual strobe values to prevent interference
                if (groupStates[group].red == groupStates[group].green &&
                    groupStates[group].red == groupStates[group].blue)
                {
                    groupStates[group].red = 0;
                    groupStates[group].green = 0;
                    groupStates[group].blue = 0;
                }

                // Apply video layer (bottom layer)
                if (videoPlaying)
                {
                    // Calculate video coordinates with offset
                    int vidX = x - videoOffsetX;
                    int vidY = y - videoOffsetY;

                    // Check if the pixel is within the video bounds
                    if (vidX >= 0 && vidX < width && vidY >= 0 && vidY < height)
                    {
                        int vidBufferIndex = (vidY * width + vidX) * 3;
                        r = frameBuffer[vidBufferIndex];
                        g = frameBuffer[vidBufferIndex + 1];
                        b = frameBuffer[vidBufferIndex + 2];

                        // Calculate perceived brightness
                        int brightness = (r * 77 + g * 150 + b * 29) >> 8;

                        // Apply threshold to video content
                        if (brightness > brightnessThreshold)
                        {
                            // Apply HSV adjustments to video
                            CRGB rgbColor(r, g, b);
                            CHSV hsvColor = rgb2hsv_approximate(rgbColor);

                            hsvColor.hue += videoAdjustments.hue;
                            hsvColor.saturation = scale8(hsvColor.saturation, videoAdjustments.saturation);
                            hsvColor.value = scale8(hsvColor.value, videoAdjustments.value);

                            hsv2rgb_rainbow(hsvColor, rgbColor);
                            r = rgbColor.r;
                            g = rgbColor.g;
                            b = rgbColor.b;
                        }
                        else
                        {
                            r = g = b = 0;
                        }
                    }
                    else
                    {
                        r = g = b = 0; // Outside video bounds, set to black
                    }
                }

                // Apply image layer (middle layer)
                if (imageLayerActive)
                {
                    // Calculate image coordinates with offset
                    int imgX = x - imageOffsetX;
                    int imgY = y - imageOffsetY;

                    // Check if the pixel is within the image bounds
                    if (imgX >= 0 && imgX < width && imgY >= 0 && imgY < height)
                    {
                        int imgBufferIndex = (imgY * width + imgX) * 3;
                        int ir = imageBuffer[imgBufferIndex];
                        int ig = imageBuffer[imgBufferIndex + 1];
                        int ib = imageBuffer[imgBufferIndex + 2];

                        // Apply brightness to the image
                        uint8_t brightness = 255; // Default to full brightness
                        for (int i = 0; i < numImages; i++)
                        {
                            if (strcmp(imageMappings[i].filename, currentImageFilename) == 0)
                            {
                                brightness = imageMappings[i].brightness;
                                break;
                            }
                        }

                        // Convert RGB to HSV
                        CRGB rgbColor(ir, ig, ib);
                        CHSV hsvColor = rgb2hsv_approximate(rgbColor);

                        // Apply HSV adjustments
                        hsvColor.hue += imageAdjustments.hue;
                        hsvColor.saturation = scale8(hsvColor.saturation, imageAdjustments.saturation);
                        hsvColor.value = scale8(hsvColor.value, imageAdjustments.value);

                        // Convert back to RGB
                        hsv2rgb_rainbow(hsvColor, rgbColor);

                        ir = rgbColor.r;
                        ig = rgbColor.g;
                        ib = rgbColor.b;

                        // Apply brightness
                        ir = (ir * brightness) >> 8;
                        ig = (ig * brightness) >> 8;
                        ib = (ib * brightness) >> 8;

                        // Determine alpha based on adjusted color intensity and original brightness
                        float alpha;
                        int maxAdjustedColor = max(max(ir, ig), ib);
                        int maxOriginalColor = max(max(imageBuffer[imgBufferIndex], imageBuffer[imgBufferIndex + 1]), imageBuffer[imgBufferIndex + 2]);

                        if (maxOriginalColor == 255 && brightness == 255)
                        {
                            // If original color was max brightness and MIDI velocity is max
                            alpha = float(maxAdjustedColor) / 255.0f;
                        }
                        else
                        {
                            // Otherwise, use a blend
                            alpha = float(maxAdjustedColor) / 255.0f * 0.5f;
                        }

                        // Alpha blending with video layer
                        r = (1 - alpha) * r + alpha * ir;
                        g = (1 - alpha) * g + alpha * ig;
                        b = (1 - alpha) * b + alpha * ib;
                    }
                    // If pixel is outside image bounds, it remains transparent (video shows through)
                }

                // Apply LED block layer (top layer, but below strobe)
                int lr = groupStates[group].red;
                int lg = groupStates[group].green;
                int lb = groupStates[group].blue;

                if (lr > 0 || lg > 0 || lb > 0) {
                    // Create separate RGB colors for each component
                    CRGB rgbColorR(lr, 0, 0);
                    CRGB rgbColorG(0, lg, 0);
                    CRGB rgbColorB(0, 0, lb);

                    // Convert each to HSV
                    CHSV hsvColorR = rgb2hsv_approximate(rgbColorR);
                    CHSV hsvColorG = rgb2hsv_approximate(rgbColorG);
                    CHSV hsvColorB = rgb2hsv_approximate(rgbColorB);

                    // Apply HSV adjustments to each component
                    hsvColorR.hue += ledBlockAdjustments.hue;
                    hsvColorG.hue += ledBlockAdjustments.hue;
                    hsvColorB.hue += ledBlockAdjustments.hue;

                    hsvColorR.saturation = scale8(hsvColorR.saturation, ledBlockAdjustments.saturation);
                    hsvColorG.saturation = scale8(hsvColorG.saturation, ledBlockAdjustments.saturation);
                    hsvColorB.saturation = scale8(hsvColorB.saturation, ledBlockAdjustments.saturation);

                    hsvColorR.value = scale8(hsvColorR.value, ledBlockAdjustments.value);
                    hsvColorG.value = scale8(hsvColorG.value, ledBlockAdjustments.value);
                    hsvColorB.value = scale8(hsvColorB.value, ledBlockAdjustments.value);

                    // Convert back to RGB
                    hsv2rgb_rainbow(hsvColorR, rgbColorR);
                    hsv2rgb_rainbow(hsvColorG, rgbColorG);
                    hsv2rgb_rainbow(hsvColorB, rgbColorB);

                    // Combine the colors using maximum value for each component
                    r = max(rgbColorR.r, max(rgbColorG.r, rgbColorB.r));
                    g = max(rgbColorR.g, max(rgbColorG.g, rgbColorB.g));
                    b = max(rgbColorR.b, max(rgbColorG.b, rgbColorB.b));
                }
            }

            leds.setPixel(ledIndex, r, g, b);
        }
    }
    ledStateChanged = true;
}

void handleStrobeNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != STROBE_MIDI_CHANNEL || pitch > 127)
        return;

    uint8_t brightness = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    // Helper function to set strobe state with color
    auto setStrobeState = [&](int x, int y, bool state, bool isWhite, bool isRed, bool isGreen, bool isBlue) {
        int ledIndex = mapXYtoLedIndex(x, y);
        int group = ledIndex / ledsPerGroup;
        strobeActive[ledIndex] = state;
        if (state && brightness > 0) {
            groupStates[group].red = isWhite || isRed ? brightness : 0;
            groupStates[group].green = isWhite || isGreen ? brightness : 0;
            groupStates[group].blue = isWhite || isBlue ? brightness : 0;
        } else {
            if (isRed) groupStates[group].red = 0;
            if (isGreen) groupStates[group].green = 0;
            if (isBlue) groupStates[group].blue = 0;
            if (isWhite) {
                groupStates[group].red = 0;
                groupStates[group].green = 0;
                groupStates[group].blue = 0;
            }
        }
    };

    // Pattern generator function
    auto applyPattern = [&](int startX, int endX, int startY, int endY, bool isWhite, bool isRed, bool isGreen, bool isBlue) {
        for (int x = startX; x < endX; x++) {
            for (int y = startY; y < endY; y++) {
                setStrobeState(x, y, isNoteOn, isWhite, isRed, isGreen, isBlue);
            }
        }
    };

    // Determine color and pattern based on note range
    bool isWhite = pitch >= 115;                    // 127-115: White
    bool isBlue = pitch >= 102 && pitch < 115;      // 114-102: Blue
    bool isRed = pitch >= 89 && pitch < 102;        // 101-89: Red
    bool isGreen = pitch >= 76 && pitch < 89;       // 88-76: Green
    bool isCyan = pitch >= 63 && pitch < 76;        // 75-63: Cyan (Blue + Green)
    bool isMagenta = pitch >= 50 && pitch < 63;     // 62-50: Magenta (Blue + Red)
    bool isYellow = pitch >= 37 && pitch < 50;      // 49-37: Yellow (Red + Green)

    // Calculate pattern index within each color range
    int patternIndex;
    if (isWhite) patternIndex = 127 - pitch;        // 0-12 for white
    else if (isBlue) patternIndex = 114 - pitch;    // 0-12 for blue
    else if (isRed) patternIndex = 101 - pitch;     // 0-12 for red
    else if (isGreen) patternIndex = 88 - pitch;    // 0-12 for green
    else if (isCyan) patternIndex = 75 - pitch;     // 0-12 for cyan
    else if (isMagenta) patternIndex = 62 - pitch;  // 0-12 for magenta
    else patternIndex = 49 - pitch;                 // 0-12 for yellow

    // Apply the appropriate pattern in the correct order
    switch (patternIndex) {
        case 0:  // Upper half
            applyPattern(0, width, 0, 48, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 1:  // Lower half
            applyPattern(0, width, 48, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 2:  // Left half
            applyPattern(0, width/2, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 3:  // Right half
            applyPattern(width/2, width, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 4:  // Left upper corner
            applyPattern(0, 24, 0, 48, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 5:  // Right upper corner
            applyPattern(width - 24, width, 0, 48, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 6:  // Left bottom corner
            applyPattern(0, 24, 48, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 7:  // Right bottom corner
            applyPattern(width - 24, width, 48, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 8:  // Column 1
            applyPattern(0, 8, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 9:  // Column 2
            applyPattern(8, 16, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 10: // Column 3
            applyPattern(16, 24, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 11: // Column 4
            applyPattern(24, 32, 0, height, isWhite,
                        isRed || isMagenta || isYellow,     // Red component
                        isGreen || isCyan || isYellow,      // Green component
                        isBlue || isCyan || isMagenta);     // Blue component
            break;
        case 12: // Column 5
            applyPattern(32, 40, 0, height, isWhite,
                        isRed || isMagenta || isYellow,
                        isGreen || isCyan || isYellow,
                        isBlue || isCyan || isMagenta);
            break;
    }

    updateLEDs();
}

void setup()
{
    Serial.begin(9600);
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn([](byte channel, byte pitch, byte velocity)
                            {
        handleLEDNoteEvent(channel, pitch, velocity, true);
        handleVideoNoteEvent(channel, pitch, velocity, true);
        handleImageNoteEvent(channel, pitch, velocity, true);
        handleRowNoteEvent(channel, pitch, velocity, true);
        handleStrobeNoteEvent(channel, pitch, velocity, true); });
    usbMIDI.setHandleNoteOff([](byte channel, byte pitch, byte velocity)
                             {
        handleLEDNoteEvent(channel, pitch, velocity, false);
        handleVideoNoteEvent(channel, pitch, velocity, false);
        handleImageNoteEvent(channel, pitch, velocity, false);
        handleRowNoteEvent(channel, pitch, velocity, false);
        handleStrobeNoteEvent(channel, pitch, velocity, false); });
    usbMIDI.setHandleControlChange(handleControlChange);

    leds.begin();
    leds.show();

    if (!SD.begin(chipSelect))
    {
        Serial.println("SD card initialization failed!");
        return;
    }
    Serial.println("SD card initialized.");

    loadMappings("video_map.txt", videoMappings, numVideos);
    loadMappings("image_map.txt", imageMappings, numImages);

    createGammaTable(); // Create gamma correction table
}

void loop()
{
    // Handle MIDI messages
    while (usbMIDI.read())
    {
        // Process all available MIDI messages
    }

    // Check if we need to update video state
    if (videoNeedsUpdate) {
        bool anyVideoActive = false;
        for (int i = 0; i < 128; i++) {
            if (activeVideoNotes[i]) {
                anyVideoActive = true;
                break;
            }
        }

        if (!anyVideoActive) {
            stopVideo();
        }
        videoNeedsUpdate = false;
    }

    // Handle video playback - use consistent timing
    unsigned long currentTime = millis();
    if (videoPlaying && (currentTime - lastVideoFrame >= frameDelay))
    {
        if (mediaFile.available() >= totalLeds * 3)
        {
            mediaFile.read(frameBuffer, totalLeds * 3);
            updateLEDs();
            lastVideoFrame = currentTime;
        }
        else if (videoLooping)
        {
            mediaFile.seek(videoStartPosition);
            lastVideoFrame = currentTime;
        }
        else
        {
            stopVideo();
        }
    }

    // Update LEDs if state has changed
    if (ledStateChanged && !leds.busy())
    {
        leds.show();
        ledStateChanged = false;
    }
}
