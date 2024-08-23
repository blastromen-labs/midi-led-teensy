#include <OctoWS2811.h>

const int NUM_PANELS = 4; // Change this to the number of panels you're using
const int LEDS_PER_PANEL = 256;
const int GROUPS_PER_PANEL = 4;

const int ledsPerStrip = LEDS_PER_PANEL;
const int totalLeds = NUM_PANELS * LEDS_PER_PANEL;
const int ledsPerGroup = LEDS_PER_PANEL / GROUPS_PER_PANEL;
const int numGroups = NUM_PANELS * GROUPS_PER_PANEL;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

struct ChannelState
{
    uint8_t velocity;
};

struct GroupState
{
    ChannelState channel1; // Blue
    ChannelState channel2; // Red
    ChannelState channel3; // Green
};

GroupState groupStates[numGroups] = {0};

bool ledStateChanged = false;
unsigned long lastUpdateTime = 0;
const unsigned long updateInterval = 10; // Minimum time between updates in milliseconds

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
    return map(velocity, 0, 127, 0, 255);
}

void updateGroupLeds(int group)
{
    uint8_t r = mapVelocityToBrightness(groupStates[group].channel2.velocity);
    uint8_t g = mapVelocityToBrightness(groupStates[group].channel3.velocity);
    uint8_t b = mapVelocityToBrightness(groupStates[group].channel1.velocity);

    int panelIndex = group / GROUPS_PER_PANEL;
    int groupWithinPanel = group % GROUPS_PER_PANEL;

    int startLed = groupWithinPanel * ledsPerGroup;
    int endLed = startLed + ledsPerGroup - 1;

    for (int i = startLed; i <= endLed; i++)
    {
        leds.setPixel(i + panelIndex * LEDS_PER_PANEL, r, g, b); // Note: RGB order for WS2811
    }
    ledStateChanged = true;
}

void handleNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    int lowestNote = 128 - numGroups;
    if (pitch >= lowestNote && pitch <= 127)
    {
        int group = 127 - pitch;
        uint8_t newVelocity = isNoteOn ? velocity : 0;

        switch (channel)
        {
        case 1:
            groupStates[group].channel1.velocity = newVelocity;
            break;
        case 2:
            groupStates[group].channel2.velocity = newVelocity;
            break;
        case 3:
            groupStates[group].channel3.velocity = newVelocity;
            break;
        default:
            return; // Ignore other channels
        }
        updateGroupLeds(group);
    }
}

void setup()
{
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
    while (usbMIDI.read())
    {
        // Process all available MIDI messages
    }

    unsigned long currentTime = millis();
    if (ledStateChanged && (currentTime - lastUpdateTime >= updateInterval))
    {
        leds.show();
        ledStateChanged = false;
        lastUpdateTime = currentTime;
    }
}
