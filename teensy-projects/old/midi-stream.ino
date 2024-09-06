#include <OctoWS2811.h>
// midi and video stream at same time
const int NUM_PANELS = 2;
const int LEDS_PER_PANEL = 256;
const int GROUPS_PER_PANEL = 4;
const int MIDI_CHANNEL = 1;

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
int bytesRead = 0;

// Brightness threshold (0-255)
const int brightnessThreshold = 10;

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
    return map(velocity, 0, 127, 0, 255);
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
        int r_stream = frameBuffer[ledIndex * 3];
        int g_stream = frameBuffer[ledIndex * 3 + 1];
        int b_stream = frameBuffer[ledIndex * 3 + 2];

        // Combine MIDI and stream colors
        leds.setPixel(ledIndex, max(r, r_stream), max(g, g_stream), max(b, b_stream));
    }
    ledStateChanged = true;
}

void handleNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (pitch < 128 - totalNotes || pitch > 127)
        return; // Ignore notes outside our range

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
            if (brightness > brightnessThreshold)
            {
                int group = ledIndex / ledsPerGroup;
                r = max(r, groupStates[group].red);
                g = max(g, groupStates[group].green);
                b = max(b, groupStates[group].blue);
                leds.setPixel(ledIndex, r, g, b);
            }
            else
            {
                int group = ledIndex / ledsPerGroup;
                leds.setPixel(ledIndex, groupStates[group].red, groupStates[group].green, groupStates[group].blue);
            }
        }
    }
    ledStateChanged = true;
}

void setup()
{
    Serial.begin(2000000);
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn([](byte channel, byte pitch, byte velocity)
                            { handleNoteEvent(channel, pitch, velocity, true); });
    usbMIDI.setHandleNoteOff([](byte channel, byte pitch, byte velocity)
                             { handleNoteEvent(channel, pitch, velocity, false); });

    leds.begin();
    leds.show();
}

void loop()
{
    // Handle MIDI messages
    while (usbMIDI.read(MIDI_CHANNEL))
    {
        // Process all available MIDI messages
    }

    // Update LEDs if state has changed
    if (ledStateChanged && !leds.busy())
    {
        leds.show();
        ledStateChanged = false;
    }

    // Handle serial data
    while (Serial.available() > 0)
    {
        frameBuffer[bytesRead] = Serial.read();
        bytesRead++;

        if (bytesRead == totalLeds * 3)
        {
            updateLEDs();
            bytesRead = 0;
        }
    }
}
