#include <OctoWS2811.h>

const int NUM_PANELS = 8;
const int LEDS_PER_PANEL = 512;

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

#define RED    0xFF0000
#define GREEN  0x00FF00
#define BLUE   0x0000FF
#define YELLOW 0xFFFF00
#define PINK   0xFF1088
#define ORANGE 0xE05800
#define WHITE  0xFFFFFF

bool ledStateChanged = false;
unsigned long lastUpdateTime = 0;
const unsigned long updateInterval = 10; // Minimum time between updates in milliseconds

void setup() {
    usbMIDI.begin();
    usbMIDI.setHandleNoteOn(handleNoteOn);
    usbMIDI.setHandleNoteOff(handleNoteOff);

    leds.begin();
    leds.show();
}

void colorFill(int panel, int color)
{
    int startLed = (panel - 1) * LEDS_PER_PANEL;  // panel 1 starts at 0, panel 2 at 512, etc.
    int endLed = startLed + LEDS_PER_PANEL;

    for (int i = startLed; i < endLed; i++)
    {
        leds.setPixel(i, color);
    }
    ledStateChanged = true;
}

// Get color based on MIDI velocity (brightness) and channel (color)
int getColor(byte channel, byte velocity) {
    int brightness = map(velocity, 0, 127, 0, 255);

    switch(channel) {
        case 1:  return (brightness << 16);              // Red
        case 2:  return (brightness << 8);               // Green
        case 3:  return brightness;                      // Blue
        case 4:  return (brightness << 16) | brightness; // Pink
        case 5:  return (brightness << 16) | (brightness << 8); // Yellow
        case 6:  return (brightness << 8) | brightness;  // Cyan
        default: return (brightness << 16) | (brightness << 8) | brightness; // White
    }
}

void handleNoteOn(byte channel, byte pitch, byte velocity)
{
    // Map MIDI notes 127-120 to panels 1-8
    if (pitch <= 127 && pitch >= (127 - NUM_PANELS + 1)) {
        int panel = 127 - pitch + 1;  // Convert note to panel number (127->1, 126->2, etc)
        int color = getColor(channel, velocity);
        colorFill(panel, color);
    }
}

void handleNoteOff(byte channel, byte pitch, byte velocity)
{
    if (pitch <= 127 && pitch >= (127 - NUM_PANELS + 1)) {
        int panel = 127 - pitch + 1;
        colorFill(panel, 0);  // Turn off the panel
    }
}

void loop() {
    while (usbMIDI.read()) {}

    if (!leds.busy()) {
        leds.show();
    }
}
