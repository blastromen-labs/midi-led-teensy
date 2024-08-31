#include <OctoWS2811.h>

const int ledsPerStrip = 256;
const int numStrips = 2;
const int numLeds = ledsPerStrip * numStrips;
const int width = 32;
const int height = 16;

DMAMEM int displayMemory[ledsPerStrip * 6];
int drawingMemory[ledsPerStrip * 6];
const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, config);

// Square properties
const int squareSize = 4;
int squareX = 0;
int squareY = 0;
int dirX = 1;
int dirY = 1;

void setup()
{
    leds.begin();
    leds.show();
}

void loop()
{
    // Clear the display
    for (int i = 0; i < numLeds; i++)
    {
        leds.setPixel(i, 0, 0, 0);
    }

    // Draw the square
    for (int y = squareY; y < squareY + squareSize; y++)
    {
        for (int x = squareX; x < squareX + squareSize; x++)
        {
            if (x >= 0 && x < width && y >= 0 && y < height)
            {
                int ledIndex = mapXYtoLedIndex(x, y);
                leds.setPixel(ledIndex, 255, 0, 0); // Red square
            }
        }
    }

    // Update square position
    squareX += dirX;
    squareY += dirY;

    // Bounce off edges
    if (squareX <= 0 || squareX + squareSize >= width)
    {
        dirX = -dirX;
    }
    if (squareY <= 0 || squareY + squareSize >= height)
    {
        dirY = -dirY;
    }

    // Show the frame
    leds.show();

    // Small delay for animation speed
    delay(100);
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
