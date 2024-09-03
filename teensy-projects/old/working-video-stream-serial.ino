#include <OctoWS2811.h>
// read video from serial stream
const int ledsPerStrip = 256;
const int numStrips = 2;
const int numLeds = ledsPerStrip * numStrips;
const int width = 32;
const int height = 16;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];
const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

byte frameBuffer[numLeds * 3];

// Brightness threshold (0-255)
const int brightnessThreshold = 10; // Adjust this value as needed

void setup()
{
    Serial.begin(2000000); // Set baud rate to 2000000
    leds.begin();
    leds.show();
}

void loop()
{
    if (Serial.available() >= numLeds * 3)
    {
        Serial.readBytes(frameBuffer, numLeds * 3);
        updateLEDs();
    }
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

            // Apply threshold
            if (brightness > brightnessThreshold)
            {
                leds.setPixel(ledIndex, r, g, b);
            }
            else
            {
                leds.setPixel(ledIndex, 0, 0, 0); // Turn off the LED
            }
        }
    }
    leds.show();
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
