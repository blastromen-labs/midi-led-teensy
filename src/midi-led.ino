#include <OctoWS2811.h>

const int NUM_PANELS = 4; // Change this to the number of panels you're using
const int LEDS_PER_PANEL = 256;
const int GROUPS_PER_PANEL = 4;
const int MIDI_CHANNEL = 1;

const int ledsPerStrip = LEDS_PER_PANEL;
const int totalLeds = NUM_PANELS * LEDS_PER_PANEL;
const int ledsPerGroup = LEDS_PER_PANEL / GROUPS_PER_PANEL;
const int numGroups = NUM_PANELS * GROUPS_PER_PANEL;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

struct GroupState
{
    uint8_t blue;
    uint8_t red;
    uint8_t green;
};

GroupState groupStates[numGroups] = {0};
bool ledStateChanged = false;

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
        leds.setPixel(i + panelIndex * LEDS_PER_PANEL, r, g, b); // Note: RGB order for WS2811
    }
    ledStateChanged = true;
}

void handleNoteEvent(byte channel, byte pitch, byte velocity, bool isNoteOn)
{
    int totalNotes = numGroups * 3; // Total notes for all colors
    int notesPerColor = numGroups;  // Notes per color (blue, red, green)

    if (pitch < 128 - totalNotes || pitch > 127)
        return; // Ignore notes outside our range

    int noteIndex = 127 - pitch;
    int colorIndex = noteIndex / notesPerColor;
    int groupIndex = noteIndex % notesPerColor;

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
    while (usbMIDI.read(MIDI_CHANNEL))
    {
        // Process all available MIDI messages
    }

    if (ledStateChanged && !leds.busy())
    {
        leds.show();
        ledStateChanged = false;
    }
}
