#include <OctoWS2811.h>
#include <SD.h>
#include <SPI.h>

const int NUM_PANELS = 2;
const int LEDS_PER_PANEL = 256;
const int GROUPS_PER_PANEL = 4;
const int LED_MIDI_CHANNEL = 1;
const int VIDEO_MIDI_CHANNEL = 2;

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

// Brightness threshold (0-255)
const int brightnessThreshold = 10;

// SD card chip select pin
const int chipSelect = BUILTIN_SDCARD;

// Video playback variables
File videoFile;
bool videoPlaying = false;
unsigned long lastFrameTime = 0;
const unsigned long frameDelay = 33; // ~30 fps

// Video file names (mapped to MIDI notes)
const int MAX_VIDEOS = 20; // Maximum number of video mappings
struct VideoMapping
{
    byte note;
    char filename[13]; // 8.3 filename format + null terminator
};

VideoMapping videoMappings[MAX_VIDEOS];
int numVideos = 0;

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
    updateGroupLeds(groupIndex);
}

void handleVideoNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (channel != VIDEO_MIDI_CHANNEL)
        return; // Ignore notes not on Video MIDI channel

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
        clearVideoBuffer();
        updateLEDs();
    }
}

void startVideo(const char *filename)
{
    if (videoPlaying)
    {
        videoFile.close();
    }
    videoFile = SD.open(filename, FILE_READ);
    if (videoFile)
    {
        videoPlaying = true;
        lastFrameTime = millis();
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
    videoFile.close();
    Serial.println("Stopped video");
}

void clearVideoBuffer()
{
    memset(frameBuffer, 0, sizeof(frameBuffer));
}

void updateLEDs()
{
    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
        {
            int ledIndex = mapXYtoLedIndex(x, y);
            int bufferIndex = (y * width + x) * 3;
            int r = frameBuffer[bufferIndex];
            int g = frameBuffer[bufferIndex + 1];
            int b = frameBuffer[bufferIndex + 2];

            // Calculate perceived brightness
            int brightness = (r * 77 + g * 150 + b * 29) >> 8;

            // Apply threshold and combine with MIDI colors
            int group = ledIndex / ledsPerGroup;
            if (brightness > brightnessThreshold)
            {
                r = max(r, groupStates[group].red);
                g = max(g, groupStates[group].green);
                b = max(b, groupStates[group].blue);
            }
            else
            {
                r = groupStates[group].red;
                g = groupStates[group].green;
                b = groupStates[group].blue;
            }

            leds.setPixel(ledIndex, r, g, b);
        }
    }
    ledStateChanged = true;
}

void loadVideoMap()
{
    File mapFile = SD.open("video_map.txt", FILE_READ);
    if (!mapFile)
    {
        Serial.println("Failed to open video_map.txt");
        return;
    }

    while (mapFile.available() && numVideos < MAX_VIDEOS)
    {
        String line = mapFile.readStringUntil('\n');
        line.trim();
        int commaIndex = line.indexOf(',');
        if (commaIndex > 0)
        {
            videoMappings[numVideos].note = line.substring(0, commaIndex).toInt();
            line.substring(commaIndex + 1).toCharArray(videoMappings[numVideos].filename, 13);
            numVideos++;
        }
    }

    mapFile.close();
    Serial.print("Loaded ");
    Serial.print(numVideos);
    Serial.println(" video mappings");
}

void setup()
{
    Serial.begin(9600);
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn([](byte channel, byte pitch, byte velocity)
                            {
        handleLEDNoteEvent(channel, pitch, velocity, true);
        handleVideoNoteEvent(channel, pitch, velocity, true); });
    usbMIDI.setHandleNoteOff([](byte channel, byte pitch, byte velocity)
                             {
        handleLEDNoteEvent(channel, pitch, velocity, false);
        handleVideoNoteEvent(channel, pitch, velocity, false); });

    leds.begin();
    leds.show();

    if (!SD.begin(chipSelect))
    {
        Serial.println("SD card initialization failed!");
        return;
    }
    Serial.println("SD card initialized.");

    loadVideoMap(); // Load video mappings from SD card
}

void loop()
{
    // Handle MIDI messages
    while (usbMIDI.read())
    {
        // Process all available MIDI messages
    }

    // Update LEDs if state has changed
    if (ledStateChanged && !leds.busy())
    {
        leds.show();
        ledStateChanged = false;
    }

    // Handle video playback
    if (videoPlaying && millis() - lastFrameTime >= frameDelay)
    {
        if (videoFile.available() >= totalLeds * 3)
        {
            videoFile.read(frameBuffer, totalLeds * 3);
            updateLEDs();
            lastFrameTime = millis();
        }
        else
        {
            stopVideo();
        }
    }
}
