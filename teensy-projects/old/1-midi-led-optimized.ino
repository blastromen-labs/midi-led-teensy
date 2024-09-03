#include <OctoWS2811.h>

const int ledsPerStrip = 512;
const int totalLeds = 512;
const int ledsPerGroup = 16;
const int numGroups = totalLeds / ledsPerGroup;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];

const int config = WS2811_GRB | WS2811_800kHz;

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
    bool isDirty;
};

GroupState groupStates[numGroups] = {0};
bool globalUpdateNeeded = false;

uint8_t mapVelocityToBrightness(uint8_t velocity)
{
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
        leds.setPixel(i, g, r, b);
    }
    groupStates[group].isDirty = false;
}

void handleNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    if (pitch <= 127 && pitch >= (127 - numGroups + 1))
    {
        int group = 127 - pitch;
        uint8_t newVelocity = isNoteOn ? velocity : 0; // Set velocity to 0 for Note Off

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
            return;
        }
        groupStates[group].isDirty = true;
        globalUpdateNeeded = true;
    }
}

void handleNoteOn(byte channel, byte pitch, byte velocity)
{
    handleNoteEvent(channel, pitch, velocity, true);
}

void handleNoteOff(byte channel, byte pitch, byte velocity)
{
    handleNoteEvent(channel, pitch, velocity, false);
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

    // Update LEDs if needed
    if (globalUpdateNeeded)
    {
        for (int i = 0; i < numGroups; i++)
        {
            if (groupStates[i].isDirty)
            {
                updateGroupLeds(i);
            }
        }
        leds.show();
        globalUpdateNeeded = false;
    }
}
