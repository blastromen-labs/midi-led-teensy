#include <OctoWS2811.h>

const int ledsPerStrip = 256; // Change this to match your setup

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];

const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

void setStripColor(int strip, int r, int g, int b)
{
    for (int i = 0; i < ledsPerStrip; i++)
    {
        leds.setPixel(i + strip * ledsPerStrip, r, g, b);
    }
}

void setup()
{
    leds.begin();
    leds.show();
}

void loop()
{
    // Clear all LEDs
    for (int i = 0; i < ledsPerStrip * 8; i++)
    {
        leds.setPixel(i, 0, 0, 0);
    }

    // Set different colors for each output
    setStripColor(0, 255, 0, 0);     // Output 1 (Orange wire) - Red
    setStripColor(1, 0, 255, 0);     // Output 2 (Green wire) - Green
    setStripColor(2, 0, 0, 255);     // Output 3 - Blue
    setStripColor(3, 255, 255, 0);   // Output 4 - Yellow
    setStripColor(4, 255, 0, 255);   // Output 5 - Magenta
    setStripColor(5, 0, 255, 255);   // Output 6 - Cyan
    setStripColor(6, 255, 255, 255); // Output 7 - White
    setStripColor(7, 128, 128, 128); // Output 8 - Gray

    leds.show();
    delay(2000);

    // Blink pattern
    for (int j = 0; j < 3; j++)
    {
        // Turn off all LEDs
        for (int i = 0; i < ledsPerStrip * 8; i++)
        {
            leds.setPixel(i, 0, 0, 0);
        }
        leds.show();
        delay(500);

        // Turn on LEDs with their respective colors
        setStripColor(0, 255, 0, 0);     // Red
        setStripColor(1, 0, 255, 0);     // Green
        setStripColor(2, 0, 0, 255);     // Blue
        setStripColor(3, 255, 255, 0);   // Yellow
        setStripColor(4, 255, 0, 255);   // Magenta
        setStripColor(5, 0, 255, 255);   // Cyan
        setStripColor(6, 255, 255, 255); // White
        setStripColor(7, 128, 128, 128); // Gray
        leds.show();
        delay(500);
    }
}
