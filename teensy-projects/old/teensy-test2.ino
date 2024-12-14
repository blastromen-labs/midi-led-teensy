#include <OctoWS2811.h>

const int NUM_PANELS = 8;
const int LEDS_PER_PANEL = 512;

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

#define RED 0xFF0000
#define GREEN 0x00FF00
#define BLUE 0x0000FF
#define YELLOW 0xFFFF00
#define PINK 0xFF1088
#define ORANGE 0xE05800
#define WHITE 0xFFFFFF

void setup() {
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
    leds.show();
}

void loop() {
    // Cycle through panels 1-4
    for (int panel = 1; panel <= NUM_PANELS; panel++) {
        colorFill(panel, BLUE);  // Light up current panel
        delay(500);

        colorFill(panel, 0);     // Turn off current panel
    }
}
