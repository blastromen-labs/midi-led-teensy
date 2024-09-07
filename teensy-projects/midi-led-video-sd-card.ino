#include <OctoWS2811.h>
#include <SD.h>
#include <SPI.h>
#include <math.h>
#include <FastLED.h> // Add this at the top of the file

// latest dev version that has video and image layers
const int NUM_PANELS = 2;
const int LEDS_PER_PANEL = 256;
const int GROUPS_PER_PANEL = 4;
const int LED_MIDI_CHANNEL = 1;
const int VIDEO_MIDI_CHANNEL = 2;
const int IMAGE_MIDI_CHANNEL = 3;

const int totalLeds = NUM_PANELS * LEDS_PER_PANEL;
const int ledsPerGroup = LEDS_PER_PANEL / GROUPS_PER_PANEL;
const int numGroups = NUM_PANELS * GROUPS_PER_PANEL;
const int totalNotes = numGroups * 3; // Total notes for all colors (blue, red, green)

const int width = 32;
const int height = 16;

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

struct HSVAdjustments
{
    uint8_t hue;
    uint8_t saturation;
    uint8_t value;
};

HSVAdjustments videoAdjustments = {0, 255, 255}; // Default to no adjustment
HSVAdjustments imageAdjustments = {0, 255, 255}; // Default to no adjustment

bool videoLooping = false;
unsigned long videoStartPosition = 0;
unsigned long videoFileSize = 0;

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

int mapXYtoLedIndex(int x, int y)
{
    int ledIndex;

    if (y < 8)
    {
        // Top half of the display
        if (x % 2 == 0)
        {
            // Even columns go down
            ledIndex = x * 8 + y;
        }
        else
        {
            // Odd columns go up
            ledIndex = x * 8 + (7 - y);
        }
    }
    else
    {
        // Bottom half of the display
        if (x % 2 == 0)
        {
            // Even columns go down
            ledIndex = 256 + x * 8 + (y - 8);
        }
        else
        {
            // Odd columns go up
            ledIndex = 256 + x * 8 + (15 - y);
        }
    }

    return ledIndex;
}

void updateGroupLeds(int group)
{
    uint8_t r = groupStates[group].red;
    uint8_t g = groupStates[group].green;
    uint8_t b = groupStates[group].blue;
    int panelIndex = group / GROUPS_PER_PANEL;
    int groupWithinPanel = group % GROUPS_PER_PANEL;
    int startLed = groupWithinPanel * ledsPerGroup;
    int endLed = startLed + ledsPerGroup - 1;

    for (int i = startLed; i <= endLed; i++)
    {
        int ledIndex = i + panelIndex * LEDS_PER_PANEL;
        int r_video = frameBuffer[ledIndex * 3];
        int g_video = frameBuffer[ledIndex * 3 + 1];
        int b_video = frameBuffer[ledIndex * 3 + 2];

        // Combine MIDI and video colors
        leds.setPixel(ledIndex, max(r, r_video), max(g, g_video), max(b, b_video));
    }
    ledStateChanged = true;
}

void handleLEDNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != LED_MIDI_CHANNEL || pitch < 128 - totalNotes || pitch > 127)
        return; // Ignore notes outside our range or not on LED MIDI channel

    int noteIndex = 127 - pitch;
    int colorIndex = noteIndex / numGroups;
    int groupIndex = noteIndex % numGroups;
    uint8_t newVelocity = isNoteOn ? mapVelocityToBrightness(velocity) : 0;

    switch (colorIndex)
    {
    case 0: // Blue
        groupStates[groupIndex].blue = newVelocity;
        break;
    case 1: // Red
        groupStates[groupIndex].red = newVelocity;
        break;
    case 2: // Green
        groupStates[groupIndex].green = newVelocity;
        break;
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
        stopVideo();
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

    if (channel == VIDEO_MIDI_CHANNEL)
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
            int bufferIndex = (y * width + x) * 3;
            int r = 0, g = 0, b = 0;

            if (videoPlaying)
            {
                r = frameBuffer[bufferIndex];
                g = frameBuffer[bufferIndex + 1];
                b = frameBuffer[bufferIndex + 2];

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

            if (imageLayerActive)
            {
                int ir = gammaTable[imageBuffer[bufferIndex]];
                int ig = gammaTable[imageBuffer[bufferIndex + 1]];
                int ib = gammaTable[imageBuffer[bufferIndex + 2]];

                // Apply brightness to the image
                uint8_t brightness = 0;
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

                // Simple alpha blending (assuming image has some transparency)
                r = (ir > 0) ? ir : r;
                g = (ig > 0) ? ig : g;
                b = (ib > 0) ? ib : b;
            }

            // Combine with MIDI colors
            int group = ledIndex / ledsPerGroup;
            r = max(r, groupStates[group].red);
            g = max(g, groupStates[group].green);
            b = max(b, groupStates[group].blue);

            leds.setPixel(ledIndex, r, g, b);
        }
    }
    ledStateChanged = true;
}

void setup()
{
    Serial.begin(9600);
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn([](byte channel, byte pitch, byte velocity)
                            {
        handleLEDNoteEvent(channel, pitch, velocity, true);
        handleVideoNoteEvent(channel, pitch, velocity, true);
        handleImageNoteEvent(channel, pitch, velocity, true); });
    usbMIDI.setHandleNoteOff([](byte channel, byte pitch, byte velocity)
                             {
        handleLEDNoteEvent(channel, pitch, velocity, false);
        handleVideoNoteEvent(channel, pitch, velocity, false);
        handleImageNoteEvent(channel, pitch, velocity, false); });
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

    // Handle video playback
    if (videoPlaying && millis() - lastFrameTime >= frameDelay)
    {
        if (mediaFile.available() >= totalLeds * 3)
        {
            mediaFile.read(frameBuffer, totalLeds * 3);
            updateLEDs();
            lastFrameTime = millis();
        }
        else if (videoLooping)
        {
            // Reached end of file, loop back to start
            mediaFile.seek(videoStartPosition);
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
