#include <OctoWS2811.h>
#include <SD.h>
#include <SPI.h>
#include <math.h>
#include <FastLED.h>

// Changelog (recent):
// 25.1.25 — serial video stream, white row strobe (MIDI ch 6, notes 103–114)
// 26.1.25 — image scale CC, video mirror CC 12
// 5.11.25 — bank selection CC 20 for /video/N/ and /image/N/ folders
//
// Panel wiring (5 columns × 3 rows, serpentine):
// |c-1|c-2|c-3|c-4|c-5|
// |1.1|3.2|4.1|6.2|7.1|
// |1.2|3.1|4.2|6.1|7.2|
// |2.1|2.2|5.1|5.2|8.1|

// === Configuration ===

const int NUM_PANELS = 8;
const int LEDS_PER_PANEL = 512;
const int GROUPS_PER_PANEL = 8;
const int PANEL_WIDTH = 8;
const int PANEL_HEIGHT = 32;
const int NUM_COLUMNS = 5;
const int NUM_ROWS = 3;

const int width = 40;
const int height = 96;

const int totalLeds = width * height;
const int FRAME_BYTES = totalLeds * 3;
const int ledsPerGroup = LEDS_PER_PANEL / GROUPS_PER_PANEL;
const int numGroups = NUM_PANELS * GROUPS_PER_PANEL;

const int LED_MIDI_CHANNEL_LEFT = 1;
const int LED_MIDI_CHANNEL_RIGHT = 2;
const int VIDEO_MIDI_CHANNEL = 3;
const int IMAGE_MIDI_CHANNEL = 4;
const int ROW_MIDI_CHANNEL = 5;
const int STROBE_MIDI_CHANNEL = 6;

const int BANK_CC = 20;
const int HUE_CC = 1;
const int SATURATION_CC = 2;
const int VALUE_CC = 3;
const int X_POSITION_CC = 4;
const int Y_POSITION_CC = 5;
const int VIDEO_SPEED_CC = 10;
const int VIDEO_DIRECTION_CC = 7;
const int VIDEO_SCALE_CC = 8;
const int VIDEO_MIRROR_CC = 12;

const int BLOCKS_PER_PANEL = 4;
const int BLOCKS_PER_COLUMN = 12;

const int brightnessThreshold = 5;
const int chipSelect = BUILTIN_SDCARD;
const unsigned long frameDelay = 33;
const int MAX_MAPPINGS = 512;
const unsigned long SERIAL_TIMEOUT = 1000;

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];
const int config = WS2811_RGB | WS2811_800kHz;
OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

// === Types ===

struct LedColor
{
    uint8_t blue;
    uint8_t red;
    uint8_t green;
};

struct Mapping
{
    byte note;
    byte bank;
    char filename[13];  // 8.3 format only (8 + dot + 3 + null)
    uint8_t brightness;
};

struct HSVAdjustments
{
    uint8_t hue;
    uint8_t saturation;
    uint8_t value;
};

struct Region
{
    int x0, x1, y0, y1;
};

// === Global state ===

LedColor groupStates[numGroups] = {0};
LedColor strobeBaseStates[numGroups] = {0};
bool ledStateChanged = false;

byte frameBuffer[FRAME_BYTES];
byte imageBuffer[FRAME_BYTES];
byte serialBuffer[FRAME_BYTES];

bool videoPlaying = false;
bool imageLayerActive = false;
File mediaFile;

Mapping videoMappings[MAX_MAPPINGS];
Mapping imageMappings[MAX_MAPPINGS];
int numVideos = 0;
int numImages = 0;

char currentImageFilename[13] = {0};

HSVAdjustments videoAdjustments = {0, 255, 255};
HSVAdjustments imageAdjustments = {0, 255, 255};
HSVAdjustments ledBlockAdjustments = {0, 255, 255};
HSVAdjustments strobeAdjustments = {0, 255, 255};

bool videoLooping = true;
unsigned long videoStartPosition = 0;
unsigned long videoFileSize = 0;

int imageOffsetX = 0;
int imageOffsetY = 0;
int videoOffsetX = 0;
int videoOffsetY = 0;

bool strobeActive[totalLeds] = {false};
bool activeVideoNotes[128] = {false};

unsigned long lastVideoFrame = 0;
bool videoNeedsUpdate = false;

float videoPlaybackSpeed = 1.0f;
bool videoSpeedModified = false;
bool videoReversed = false;
bool videoDirectionModified = false;

float videoScale = 1.0f;
bool videoScaleModified = false;

float imageScale = 1.0f;
bool imageScaleModified = false;

bool videoMirrored = false;
bool videoMirrorModified = false;

byte currentVideoBank = 0;
byte currentImageBank = 0;

unsigned long lastSerialDataTime = 0;
bool serialStreamActive = false;

static uint16_t xyToLed[totalLeds];  // precomputed in setup(); indices fit in 16 bits (max 3839)

static const Region STROBE_PATTERNS[] = {
    {0, width, 0, 48},
    {0, width, 48, height},
    {0, width / 2, 0, height},
    {width / 2, width, 0, height},
    {0, 24, 0, 48},
    {width - 24, width, 0, 48},
    {0, 24, 48, height},
    {width - 24, width, 48, height},
    {0, 8, 0, height},
    {8, 16, 0, height},
    {16, 24, 0, height},
    {24, 32, 0, height},
    {32, 40, 0, height},
    {0, width, 0, height},
};

// === Forward declarations ===

void updateLEDs();
void startVideo(const char *filename, byte bank);
void stopVideo();
void startImage(const char *filename, byte bank);
void stopImage();
void handleStrobeNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn);
void dispatchNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn);

// === Coordinate / color utilities ===

int mapCCToOffset(int value, int maxOffset)
{
    if (value == 64)
        return 0;
    if (value < 64)
        return map(value, 0, 63, -maxOffset, -1);
    return map(value, 65, 127, 1, maxOffset);
}

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
    return map(velocity, 0, 127, 0, 255);
}

float mapCCScale(byte value)
{
    if (value == 64)
        return 1.0f;
    if (value < 64)
    {
        float normalized = value / 64.0f;
        return 0.25f + (pow(normalized, 2) * 0.75f);
    }
    float normalized = (value - 64) / 63.0f;
    return 1.0f + (pow(normalized, 2) * 3.0f);
}

inline int perceivedBrightness(int r, int g, int b)
{
    return (r * 77 + g * 150 + b * 29) >> 8;
}

bool isHSVAdjustmentsNeutral(const HSVAdjustments &adj)
{
    return adj.hue == 0 && adj.saturation == 255 && adj.value == 255;
}

void applyHSVAdjustments(int &r, int &g, int &b, const HSVAdjustments &adj)
{
    if (isHSVAdjustmentsNeutral(adj))
        return;

    CRGB rgbColor(r, g, b);
    CHSV hsvColor = rgb2hsv_approximate(rgbColor);

    hsvColor.hue += adj.hue;
    hsvColor.saturation = scale8(hsvColor.saturation, adj.saturation);
    hsvColor.value = scale8(hsvColor.value, adj.value);

    hsv2rgb_rainbow(hsvColor, rgbColor);
    r = rgbColor.r;
    g = rgbColor.g;
    b = rgbColor.b;
}

int mapXYtoLedIndex(int x, int y)
{
    int panel_column = x / PANEL_WIDTH;
    int panel_row = y / PANEL_HEIGHT;
    int x_in_panel = x % PANEL_WIDTH;
    int y_in_panel = y % PANEL_HEIGHT;

    int panel_index;
    if (panel_column % 2 == 0)
        panel_index = panel_column * NUM_ROWS + panel_row;
    else
        panel_index = panel_column * NUM_ROWS + (NUM_ROWS - 1 - panel_row);

    int led_in_panel;
    if (panel_column % 2 == 0)
    {
        if (y_in_panel % 2 == 0)
            led_in_panel = y_in_panel * PANEL_WIDTH + (PANEL_WIDTH - 1 - x_in_panel);
        else
            led_in_panel = y_in_panel * PANEL_WIDTH + x_in_panel;
    }
    else
    {
        int y_reversed = (PANEL_HEIGHT - 1) - y_in_panel;
        if (y_reversed % 2 == 0)
            led_in_panel = y_reversed * PANEL_WIDTH + x_in_panel;
        else
            led_in_panel = y_reversed * PANEL_WIDTH + (PANEL_WIDTH - 1 - x_in_panel);
    }

    return panel_index * (PANEL_WIDTH * PANEL_HEIGHT) + led_in_panel;
}

void initXyToLedTable()
{
    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
            xyToLed[y * width + x] = (uint16_t)mapXYtoLedIndex(x, y);
    }
}

inline int ledIndexAt(int x, int y)
{
    return xyToLed[y * width + x];
}

void setGroupColor(int group, int colorSection, uint8_t brightness)
{
    switch (colorSection)
    {
    case 0:
        groupStates[group].blue = brightness;
        break;
    case 1:
        groupStates[group].red = brightness;
        break;
    case 2:
        groupStates[group].green = brightness;
        break;
    }
}

bool sampleLayer(const byte *buffer, int x, int y, float scale, int offsetX, int offsetY, bool mirror, int &r, int &g, int &b, int *outBufferIndex = nullptr)
{
    int centerX = width / 2;
    int centerY = height / 2;
    float srcXf = (x - centerX) / scale + centerX - offsetX;
    float srcYf = (y - centerY) / scale + centerY - offsetY;

    if (srcXf < 0 || srcXf >= width || srcYf < 0 || srcYf >= height)
        return false;

    int srcX = (int)srcXf;
    int srcY = (int)srcYf;

    if (mirror)
        srcX = (width - 1) - srcX;

    int idx = (srcY * width + srcX) * 3;
    r = buffer[idx];
    g = buffer[idx + 1];
    b = buffer[idx + 2];
    if (outBufferIndex)
        *outBufferIndex = idx;
    return true;
}

// === Media utilities ===

void buildMediaPath(const char *folder, byte bank, const char *filename, char *out, size_t outLen)
{
    snprintf(out, outLen, "/%s/%d/%s", folder, bank, filename);
}

Mapping *findMapping(Mapping *list, int count, byte note, byte bank)
{
    for (int i = 0; i < count; i++)
    {
        if (list[i].note == note && list[i].bank == bank)
            return &list[i];
    }
    return nullptr;
}

unsigned long lastFramePosition(unsigned long fileSize)
{
    unsigned long pos = fileSize - (fileSize % FRAME_BYTES);
    if (pos >= (unsigned long)FRAME_BYTES)
        pos -= FRAME_BYTES;
    return pos;
}

void seekToLastFrame(File &file, unsigned long fileSize)
{
    file.seek(lastFramePosition(fileSize));
}

// === MIDI handlers ===

void handleLEDNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if ((channel != LED_MIDI_CHANNEL_LEFT && channel != LED_MIDI_CHANNEL_RIGHT) || pitch > 127)
        return;

    int noteIndex = 127 - pitch;
    const int NOTES_PER_COLOR = BLOCKS_PER_COLUMN;
    const int NOTES_PER_COLUMN = NOTES_PER_COLOR * 3;

    int column;
    if (channel == LED_MIDI_CHANNEL_LEFT)
    {
        column = noteIndex / NOTES_PER_COLUMN;
        if (column > 2)
            return;
    }
    else
    {
        column = 3 + (noteIndex / NOTES_PER_COLUMN);
        if (column > 4)
            return;
    }

    int remaining = noteIndex % NOTES_PER_COLUMN;
    int colorSection = remaining / NOTES_PER_COLOR;
    int blockInColumn = remaining % NOTES_PER_COLOR;
    int panelInColumn = blockInColumn / BLOCKS_PER_PANEL;
    int blockInPanel = blockInColumn % BLOCKS_PER_PANEL;

    if (column % 2 == 1)
    {
        panelInColumn = 2 - panelInColumn;
        blockInPanel = BLOCKS_PER_PANEL - 1 - blockInPanel;
    }

    int panel_index = column * NUM_ROWS + panelInColumn;
    int groupIndex = (panel_index * BLOCKS_PER_PANEL) + blockInPanel;
    uint8_t brightness = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    setGroupColor(groupIndex, colorSection, brightness);
    ledStateChanged = true;
}

void handleRowNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != ROW_MIDI_CHANNEL || pitch > 127)
        return;

    int noteIndex = 127 - pitch;
    const int ROWS_PER_COLOR = 12;
    int colorSection = noteIndex / ROWS_PER_COLOR;
    int rowIndex = noteIndex % ROWS_PER_COLOR;

    if (colorSection >= 3)
        return;

    rowIndex = rowIndex * 8;
    uint8_t brightness = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    for (int x = 0; x < width; x++)
    {
        for (int y = rowIndex; y < rowIndex + 8; y++)
        {
            int group = ledIndexAt(x, y) / ledsPerGroup;
            setGroupColor(group, colorSection, brightness);
        }
    }

    ledStateChanged = true;
}

void loadMappings(const char *filename, Mapping *mappings, int &count)
{
    Serial.print("Loading mappings from: ");
    Serial.println(filename);

    File mapFile = SD.open(filename, FILE_READ);
    if (!mapFile)
    {
        Serial.print("ERROR: Failed to open mapping file: ");
        Serial.println(filename);
        return;
    }

    count = 0;
    int skippedLines = 0;
    while (mapFile.available())
    {
        String line = mapFile.readStringUntil('\n');
        line.trim();

        if (line.length() == 0)
            continue;

        if (count >= MAX_MAPPINGS)
        {
            skippedLines++;
            continue;
        }

        int firstComma = line.indexOf(',');
        if (firstComma > 0)
        {
            int secondComma = line.indexOf(',', firstComma + 1);
            if (secondComma > firstComma)
            {
                mappings[count].note = line.substring(0, firstComma).toInt();
                mappings[count].bank = line.substring(firstComma + 1, secondComma).toInt();
                line.substring(secondComma + 1).toCharArray(mappings[count].filename, 13);
                mappings[count].brightness = 255;  // full brightness until MIDI velocity overrides

                Serial.print("  Loaded mapping #");
                Serial.print(count);
                Serial.print(": note=");
                Serial.print(mappings[count].note);
                Serial.print(" bank=");
                Serial.print(mappings[count].bank);
                Serial.print(" file=");
                Serial.println(mappings[count].filename);

                count++;
            }
        }
    }

    Serial.print("Total mappings loaded from ");
    Serial.print(filename);
    Serial.print(": ");
    Serial.println(count);

    if (skippedLines > 0)
    {
        Serial.print("WARNING: ");
        Serial.print(skippedLines);
        Serial.print(" mappings were skipped due to MAX_MAPPINGS limit (");
        Serial.print(MAX_MAPPINGS);
        Serial.println(")");
        Serial.println("Consider increasing MAX_MAPPINGS constant if you need more mappings.");
    }

    mapFile.close();
}

void handleVideoNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != VIDEO_MIDI_CHANNEL)
        return;

    if (isNoteOn && velocity > 0)
    {
        if (videoPlaying)
        {
            stopVideo();
            memset(activeVideoNotes, 0, sizeof(activeVideoNotes));
        }

        activeVideoNotes[pitch] = true;

        Mapping *mapping = findMapping(videoMappings, numVideos, pitch, currentVideoBank);
        if (mapping)
        {
            startVideo(mapping->filename, mapping->bank);
            return;
        }
    }
    else
    {
        activeVideoNotes[pitch] = false;
    }

    videoNeedsUpdate = true;
}

void handleImageNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != IMAGE_MIDI_CHANNEL)
        return;

    if (isNoteOn)
    {
        Mapping *mapping = findMapping(imageMappings, numImages, pitch, currentImageBank);
        if (mapping)
        {
            mapping->brightness = mapVelocityToBrightness(velocity);
            startImage(mapping->filename, mapping->bank);
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

    if (channel == VIDEO_MIDI_CHANNEL)
    {
        if (control == BANK_CC)
        {
            currentVideoBank = value;
            return;
        }
        if (control == VIDEO_DIRECTION_CC)
        {
            videoDirectionModified = true;
            videoReversed = (value == 127);
            return;
        }
        if (control == VIDEO_SPEED_CC)
        {
            videoSpeedModified = true;
            if (value == 0)
                videoPlaybackSpeed = 0.0f;
            else if (value == 64)
                videoPlaybackSpeed = 1.0f;
            else if (value < 64)
            {
                float normalized = (value - 1) / 63.0f;
                videoPlaybackSpeed = 0.25f + (pow(normalized, 2) * 0.75f);
            }
            else
            {
                float normalized = (value - 64) / 63.0f;
                videoPlaybackSpeed = pow(64, normalized);
            }
            return;
        }
        if (control == VIDEO_SCALE_CC)
        {
            videoScaleModified = true;
            videoScale = mapCCScale(value);
            return;
        }
        if (control == VIDEO_MIRROR_CC)
        {
            videoMirrorModified = true;
            videoMirrored = (value == 127);
            return;
        }
        adjustments = &videoAdjustments;
    }
    else if (channel == LED_MIDI_CHANNEL_LEFT || channel == LED_MIDI_CHANNEL_RIGHT)
    {
        adjustments = &ledBlockAdjustments;
    }
    else if (channel == IMAGE_MIDI_CHANNEL)
    {
        if (control == BANK_CC)
        {
            currentImageBank = value;
            return;
        }
        if (control == VIDEO_SCALE_CC)
        {
            imageScaleModified = true;
            imageScale = mapCCScale(value);
            ledStateChanged = true;
            return;
        }
        adjustments = &imageAdjustments;
    }
    else if (channel == STROBE_MIDI_CHANNEL)
    {
        adjustments = &strobeAdjustments;
    }

    if (adjustments)
    {
        switch (control)
        {
        case HUE_CC:
            adjustments->hue = value * 2;
            break;
        case SATURATION_CC:
            adjustments->saturation = map(value, 0, 127, 0, 255);
            break;
        case VALUE_CC:
            adjustments->value = map(value, 0, 127, 0, 255);
            break;
        case X_POSITION_CC:
            if (channel == VIDEO_MIDI_CHANNEL)
                videoOffsetX = mapCCToOffset(value, width);
            else if (channel == IMAGE_MIDI_CHANNEL)
                imageOffsetX = mapCCToOffset(value, width);
            break;
        case Y_POSITION_CC:
            if (channel == VIDEO_MIDI_CHANNEL)
                videoOffsetY = mapCCToOffset(value, height);
            else if (channel == IMAGE_MIDI_CHANNEL)
                imageOffsetY = mapCCToOffset(value, height);
            break;
        }

        ledStateChanged = true;
    }
}

void dispatchNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    handleLEDNoteEvent(channel, pitch, velocity, isNoteOn);
    handleVideoNoteEvent(channel, pitch, velocity, isNoteOn);
    handleImageNoteEvent(channel, pitch, velocity, isNoteOn);
    handleRowNoteEvent(channel, pitch, velocity, isNoteOn);
    handleStrobeNoteEvent(channel, pitch, velocity, isNoteOn);
}

// === Media I/O ===

void startVideo(const char *filename, byte bank)
{
    if (videoPlaying)
        stopVideo();

    char fullPath[32];
    buildMediaPath("video", bank, filename, fullPath, sizeof(fullPath));

    mediaFile = SD.open(fullPath, FILE_READ);
    if (!mediaFile)
        return;

    videoPlaying = true;
    videoFileSize = mediaFile.size();

    if (videoDirectionModified && videoReversed)
    {
        seekToLastFrame(mediaFile, videoFileSize);
        videoStartPosition = lastFramePosition(videoFileSize);

        if (mediaFile.available())
        {
            mediaFile.read(frameBuffer, FRAME_BYTES);
            ledStateChanged = true;
        }
    }
    else
    {
        videoStartPosition = 0;
        mediaFile.seek(videoStartPosition);
    }

    lastVideoFrame = millis();
}

void stopVideo()
{
    if (videoPlaying)
    {
        if (mediaFile)
            mediaFile.close();
        videoPlaying = false;
        videoFileSize = 0;
        videoStartPosition = 0;
        memset(frameBuffer, 0, FRAME_BYTES);
        ledStateChanged = true;
    }
}

void startImage(const char *filename, byte bank)
{
    char fullPath[32];
    buildMediaPath("image", bank, filename, fullPath, sizeof(fullPath));

    File imageFile = SD.open(fullPath, FILE_READ);
    if (imageFile)
    {
        imageFile.read(imageBuffer, FRAME_BYTES);
        imageFile.close();
        imageLayerActive = true;
        strncpy(currentImageFilename, filename, 12);
        currentImageFilename[12] = '\0';
        updateLEDs();
    }
}

void stopImage()
{
    imageLayerActive = false;
    memset(imageBuffer, 0, sizeof(imageBuffer));
    updateLEDs();
}

// === Compositing ===

void updateLEDs()
{
    uint8_t currentImageBrightness = 255;
    if (imageLayerActive)
    {
        for (int i = 0; i < numImages; i++)
        {
            if (strcmp(imageMappings[i].filename, currentImageFilename) == 0)
            {
                currentImageBrightness = imageMappings[i].brightness;
                break;
            }
        }
    }

    const float vidScale = videoScaleModified ? videoScale : 1.0f;
    const float imgScale = imageScaleModified ? imageScale : 1.0f;
    const bool mirror = videoMirrorModified && videoMirrored;

    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
        {
            int ledIndex = ledIndexAt(x, y);
            int group = ledIndex / ledsPerGroup;

            if (strobeActive[ledIndex])
            {
                uint8_t r = strobeBaseStates[group].red;
                uint8_t g = strobeBaseStates[group].green;
                uint8_t b = strobeBaseStates[group].blue;

                if (r > 0 || g > 0 || b > 0)
                {
                    int sr = r, sg = g, sb = b;
                    applyHSVAdjustments(sr, sg, sb, strobeAdjustments);
                    r = sr;
                    g = sg;
                    b = sb;
                }

                leds.setPixel(ledIndex, r, g, b);
                continue;
            }

            int r = 0, g = 0, b = 0;

            if (groupStates[group].red > 0 &&
                groupStates[group].red == groupStates[group].green &&
                groupStates[group].red == groupStates[group].blue)
            {
                r = groupStates[group].red;
                g = groupStates[group].green;
                b = groupStates[group].blue;
            }
            else
            {
                if (groupStates[group].red == groupStates[group].green &&
                    groupStates[group].red == groupStates[group].blue)
                {
                    groupStates[group].red = 0;
                    groupStates[group].green = 0;
                    groupStates[group].blue = 0;
                }

                if (videoPlaying)
                {
                    int vr, vg, vb;
                    if (sampleLayer(frameBuffer, x, y, vidScale, videoOffsetX, videoOffsetY, mirror, vr, vg, vb))
                    {
                        if (perceivedBrightness(vr, vg, vb) > brightnessThreshold)
                        {
                            applyHSVAdjustments(vr, vg, vb, videoAdjustments);
                            r = vr;
                            g = vg;
                            b = vb;
                        }
                    }
                }

                if (imageLayerActive)
                {
                    int ir, ig, ib, imgBufferIndex;
                    if (sampleLayer(imageBuffer, x, y, imgScale, imageOffsetX, imageOffsetY, false, ir, ig, ib, &imgBufferIndex))
                    {
                        applyHSVAdjustments(ir, ig, ib, imageAdjustments);

                        ir = (ir * currentImageBrightness) >> 8;
                        ig = (ig * currentImageBrightness) >> 8;
                        ib = (ib * currentImageBrightness) >> 8;

                        float alpha;
                        int maxAdjustedColor = max(max(ir, ig), ib);
                        int maxOriginalColor = max(max(imageBuffer[imgBufferIndex], imageBuffer[imgBufferIndex + 1]), imageBuffer[imgBufferIndex + 2]);

                        if (maxOriginalColor == 255 && currentImageBrightness == 255)
                            alpha = float(maxAdjustedColor) / 255.0f;
                        else
                            alpha = float(maxAdjustedColor) / 255.0f * 0.5f;

                        r = (1 - alpha) * r + alpha * ir;
                        g = (1 - alpha) * g + alpha * ig;
                        b = (1 - alpha) * b + alpha * ib;
                    }
                }

                int lr = groupStates[group].red;
                int lg = groupStates[group].green;
                int lb = groupStates[group].blue;

                if (lr > 0 || lg > 0 || lb > 0)
                {
                    if (isHSVAdjustmentsNeutral(ledBlockAdjustments))
                    {
                        r = lr;
                        g = lg;
                        b = lb;
                    }
                    else
                    {
                        CRGB rgbColorR(lr, 0, 0);
                        CRGB rgbColorG(0, lg, 0);
                        CRGB rgbColorB(0, 0, lb);

                        CHSV hsvColorR = rgb2hsv_approximate(rgbColorR);
                        CHSV hsvColorG = rgb2hsv_approximate(rgbColorG);
                        CHSV hsvColorB = rgb2hsv_approximate(rgbColorB);

                        hsvColorR.hue += ledBlockAdjustments.hue;
                        hsvColorG.hue += ledBlockAdjustments.hue;
                        hsvColorB.hue += ledBlockAdjustments.hue;

                        hsvColorR.saturation = scale8(hsvColorR.saturation, ledBlockAdjustments.saturation);
                        hsvColorG.saturation = scale8(hsvColorG.saturation, ledBlockAdjustments.saturation);
                        hsvColorB.saturation = scale8(hsvColorB.saturation, ledBlockAdjustments.saturation);

                        hsvColorR.value = scale8(hsvColorR.value, ledBlockAdjustments.value);
                        hsvColorG.value = scale8(hsvColorG.value, ledBlockAdjustments.value);
                        hsvColorB.value = scale8(hsvColorB.value, ledBlockAdjustments.value);

                        hsv2rgb_rainbow(hsvColorR, rgbColorR);
                        hsv2rgb_rainbow(hsvColorG, rgbColorG);
                        hsv2rgb_rainbow(hsvColorB, rgbColorB);

                        r = max(rgbColorR.r, max(rgbColorG.r, rgbColorB.r));
                        g = max(rgbColorR.g, max(rgbColorG.g, rgbColorB.g));
                        b = max(rgbColorR.b, max(rgbColorG.b, rgbColorB.b));
                    }
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

    auto setStrobeState = [&](int x, int y, bool state, bool isWhite, bool isRed, bool isGreen, bool isBlue)
    {
        int ledIndex = ledIndexAt(x, y);
        int group = ledIndex / ledsPerGroup;
        strobeActive[ledIndex] = state;
        if (state && brightness > 0)
        {
            strobeBaseStates[group].red = isWhite || isRed ? brightness : 0;
            strobeBaseStates[group].green = isWhite || isGreen ? brightness : 0;
            strobeBaseStates[group].blue = isWhite || isBlue ? brightness : 0;
        }
        else
        {
            strobeBaseStates[group].red = 0;
            strobeBaseStates[group].green = 0;
            strobeBaseStates[group].blue = 0;
        }
    };

    auto applyPattern = [&](int startX, int endX, int startY, int endY, bool isWhite, bool isRed, bool isGreen, bool isBlue)
    {
        for (int px = startX; px < endX; px++)
        {
            for (int py = startY; py < endY; py++)
                setStrobeState(px, py, isNoteOn, isWhite, isRed, isGreen, isBlue);
        }
    };

    if (pitch >= 103 && pitch <= 114)
    {
        int rowIndex = (114 - pitch) * 8;
        for (int px = 0; px < width; px++)
        {
            for (int py = rowIndex; py < rowIndex + 8; py++)
                setStrobeState(px, py, isNoteOn, true, false, false, false);
        }
        ledStateChanged = true;

        if (!isNoteOn)
        {
            updateLEDs();
            if (!leds.busy())
                leds.show();
        }
        return;
    }

    bool isWhite = pitch >= 115;
    bool isBlue = pitch >= 89 && pitch < 103;
    bool isRed = pitch >= 76 && pitch < 89;
    bool isGreen = pitch >= 63 && pitch < 76;
    bool isCyan = pitch >= 50 && pitch < 63;
    bool isMagenta = pitch >= 37 && pitch < 50;
    bool isYellow = pitch >= 24 && pitch < 37;

    int patternIndex;
    if (isWhite)
        patternIndex = 127 - pitch;
    else if (isBlue)
        patternIndex = 102 - pitch;
    else if (isRed)
        patternIndex = 88 - pitch;
    else if (isGreen)
        patternIndex = 75 - pitch;
    else if (isCyan)
        patternIndex = 62 - pitch;
    else if (isMagenta)
        patternIndex = 49 - pitch;
    else
        patternIndex = 36 - pitch;

    const int patternCount = sizeof(STROBE_PATTERNS) / sizeof(STROBE_PATTERNS[0]);
    if (patternIndex >= 0 && patternIndex < patternCount)
    {
        const Region &region = STROBE_PATTERNS[patternIndex];
        bool useR = isWhite || isRed || isMagenta || isYellow;
        bool useG = isWhite || isGreen || isCyan || isYellow;
        bool useB = isWhite || isBlue || isCyan || isMagenta;
        applyPattern(region.x0, region.x1, region.y0, region.y1, isWhite, useR, useG, useB);
    }

    ledStateChanged = true;

    if (!isNoteOn)
    {
        updateLEDs();
        if (!leds.busy())
            leds.show();
    }
}

bool anyVideoNotesActive()
{
    for (int i = 0; i < 128; i++)
    {
        if (activeVideoNotes[i])
            return true;
    }
    return false;
}

void startupTest()
{
    for (int flash = 0; flash < 3; flash++)
    {
        for (int i = 0; i < 768; i++)
            leds.setPixel(i, 0, 0, 255);
        leds.show();
        delay(500);

        for (int i = 0; i < 768; i++)
            leds.setPixel(i, 0, 0, 0);
        leds.show();
        delay(500);
    }
}

void clearScreen()
{
    for (int i = 0; i < totalLeds; i++)
        leds.setPixel(i, 0, 0, 0);
    leds.show();
    memset(frameBuffer, 0, FRAME_BYTES);
}

void handleSerialVideo()
{
    unsigned long currentTime = millis();
    int bytesRead = Serial.readBytes((char *)serialBuffer, FRAME_BYTES);

    if (bytesRead == FRAME_BYTES)
    {
        if (!serialStreamActive)
            serialStreamActive = true;

        memcpy(frameBuffer, serialBuffer, FRAME_BYTES);
        lastSerialDataTime = currentTime;

        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                int ledIndex = ledIndexAt(x, y);
                int bufferIndex = (y * width + x) * 3;
                int r = frameBuffer[bufferIndex];
                int g = frameBuffer[bufferIndex + 1];
                int b = frameBuffer[bufferIndex + 2];

                if (perceivedBrightness(r, g, b) > brightnessThreshold)
                    leds.setPixel(ledIndex, r, g, b);
                else
                    leds.setPixel(ledIndex, 0, 0, 0);
            }
        }

        if (!leds.busy())
            leds.show();
    }
}

void handleSDVideo()
{
    if (videoNeedsUpdate)
    {
        if (!anyVideoNotesActive())
            stopVideo();
        videoNeedsUpdate = false;
    }

    if (videoPlaying && !mediaFile.available())
    {
        if (videoLooping)
            mediaFile.seek(videoStartPosition);
        else
            stopVideo();
    }

    bool isReversed = videoDirectionModified ? videoReversed : false;
    float currentSpeed = videoSpeedModified ? videoPlaybackSpeed : 1.0f;
    unsigned long currentTime = millis();

    unsigned long adjustedDelay = (currentSpeed > 0.0f)
                                      ? (frameDelay / currentSpeed)
                                      : 99999999UL;

    if (videoPlaying && (currentTime - lastVideoFrame >= adjustedDelay))
    {
        if (isReversed)
        {
            unsigned long currentPos = mediaFile.position();

            if (currentPos >= (unsigned long)FRAME_BYTES * 2)
                mediaFile.seek(currentPos - FRAME_BYTES * 2);
            else if (currentPos >= (unsigned long)FRAME_BYTES)
                mediaFile.seek(currentPos - FRAME_BYTES);
            else if (videoLooping)
                seekToLastFrame(mediaFile, videoFileSize);
            else
            {
                stopVideo();
                return;
            }
        }

        if (mediaFile.available())
        {
            mediaFile.read(frameBuffer, FRAME_BYTES);
            lastVideoFrame = currentTime;
            ledStateChanged = true;

            if (isReversed && mediaFile.position() <= (unsigned long)FRAME_BYTES && videoLooping)
                seekToLastFrame(mediaFile, videoFileSize);
        }
        else if (videoLooping)
        {
            if (isReversed)
                seekToLastFrame(mediaFile, videoFileSize);
            else
                mediaFile.seek(videoStartPosition);

            if (mediaFile.available())
            {
                mediaFile.read(frameBuffer, FRAME_BYTES);
                lastVideoFrame = currentTime;
                ledStateChanged = true;
            }
        }
        else
        {
            stopVideo();
        }
    }
}

// === Setup / loop ===

void setup()
{
    Serial.begin(2000000);
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn([](byte channel, byte pitch, byte velocity)
                            { dispatchNoteEvent(channel, pitch, velocity, true); });
    usbMIDI.setHandleNoteOff([](byte channel, byte pitch, byte velocity)
                             { dispatchNoteEvent(channel, pitch, velocity, false); });
    usbMIDI.setHandleControlChange(handleControlChange);

    leds.begin();
    leds.show();

    initXyToLedTable();

    if (!SD.begin(chipSelect))
    {
        Serial.println("SD card initialization failed!");
        return;
    }
    Serial.println("SD card initialized.");
    Serial.println("========================================");

    loadMappings("video_map.txt", videoMappings, numVideos);
    Serial.println("========================================");
    loadMappings("image_map.txt", imageMappings, numImages);
    Serial.println("========================================");

    startupTest();
}

void loop()
{
    while (usbMIDI.read())
    {
    }

    unsigned long currentTime = millis();

    if (Serial.available() > 0)
    {
        handleSerialVideo();
    }
    else if (serialStreamActive && (currentTime - lastSerialDataTime > SERIAL_TIMEOUT))
    {
        clearScreen();
        serialStreamActive = false;
        handleSDVideo();
    }
    else if (!serialStreamActive)
    {
        handleSDVideo();
    }

    if (ledStateChanged && !leds.busy())
    {
        updateLEDs();
        leds.show();
        ledStateChanged = false;
    }
}
