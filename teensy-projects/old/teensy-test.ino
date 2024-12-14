#include <OctoWS2811.h>

const int LEDS_PER_PANEL = 512;

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

void setup()
{
    leds.begin();
    leds.show();
}

#define RED 0xFF0000
#define GREEN 0x00FF00
#define BLUE 0x0000FF
#define YELLOW 0xFFFF00
#define PINK 0xFF1088
#define ORANGE 0xE05800
#define WHITE 0xFFFFFF

// New function to fill all LEDs at once
void colorFill(int color)
{
    for (int i = 0; i < leds.numPixels(); i++)
    {
        leds.setPixel(i, color);
    }
    leds.show();
}

void loop()
{
    // Cycle through each color
    colorFill(RED);
    delay(1000);  // Keep on for 1 second
    colorFill(0); // Turn off all LEDs
    delay(1000);  // Stay off for 1 second

    colorFill(GREEN);
    delay(1000);
    colorFill(0);
    delay(1000);

    colorFill(BLUE);
    delay(1000);
    colorFill(0);
    delay(1000);

    colorFill(YELLOW);
    delay(1000);
    colorFill(0);
    delay(1000);

    colorFill(PINK);
    delay(1000);
    colorFill(0);
    delay(1000);

    colorFill(ORANGE);
    delay(1000);
    colorFill(0);
    delay(1000);

    colorFill(WHITE);
    delay(1000);
    colorFill(0);
    delay(1000);
}