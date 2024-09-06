#include <OctoWS2811.h>

const int ledsPerStrip = 256;
const int totalLeds = 256;
const int ledsPerGroup = 64;
const int numGroups = totalLeds / ledsPerGroup;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

bool ledStateChanged = false;
unsigned long lastUpdateTime = 0;
const unsigned long updateInterval = 8; // Minimum time between updates in milliseconds

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

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
    // Map MIDI velocity (0-127) to LED brightness (0-255)
    return map(velocity, 0, 127, 0, 255);
}

void updateGroupLeds(int group)
{
    uint8_t r = mapVelocityToBrightness(groupStates[group].channel2.velocity);
    uint8_t g = mapVelocityToBrightness(groupStates[group].channel3.velocity);
    uint8_t b = mapVelocityToBrightness(groupStates[group].channel1.velocity);

    int startLed = group * ledsPerGroup;
    int endLed = min(startLed + ledsPerGroup - 1, totalLeds - 1);

    for (int i = startLed; i <= endLed; i++)
    {
        leds.setPixel(i, r, g, b); // Note: GRB order for WS2815
    }
    ledStateChanged = true;
}

void handleNoteOn(byte channel, byte pitch, byte velocity)
{
    if (pitch <= 127 && pitch >= (127 - numGroups + 1))
    {
        int group = 127 - pitch;
        switch (channel)
        {
        case 1:
            groupStates[group].channel1.velocity = velocity;
            break;
        case 2:
            groupStates[group].channel2.velocity = velocity;
            break;
        case 3:
            groupStates[group].channel3.velocity = velocity;
            break;
        default:
            return; // Ignore other channels
        }
        updateGroupLeds(group);
    }
}

void handleNoteOff(byte channel, byte pitch, byte velocity)
{
    if (pitch <= 127 && pitch >= (127 - numGroups + 1))
    {
        int group = 127 - pitch;
        switch (channel)
        {
        case 1:
            groupStates[group].channel1.velocity = 0;
            break;
        case 2:
            groupStates[group].channel2.velocity = 0;
            break;
        case 3:
            groupStates[group].channel3.velocity = 0;
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
    usbMIDI.setHandleNoteOn(handleNoteOn);
    usbMIDI.setHandleNoteOff(handleNoteOff);

    leds.begin();
    leds.show();
}

void loop()
{
    // Process all available MIDI messages
    while (usbMIDI.read())
    {
    }

    unsigned long currentTime = millis();
    if (ledStateChanged && (currentTime - lastUpdateTime >= updateInterval))
    {
        leds.show();
        ledStateChanged = false;
        lastUpdateTime = currentTime;
    }
}
