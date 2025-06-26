#include <OctoWS2811.h>

// Panel and LED configuration
const int NUM_PANELS = 8;
const int LEDS_PER_PANEL = 512;
const int width = 40;
const int height = 96;
const int totalLeds = 3840;
const int frameSize = totalLeds * 3;

DMAMEM int displayMemory[LEDS_PER_PANEL * 6];
int drawingMemory[LEDS_PER_PANEL * 6];
const int config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(LEDS_PER_PANEL, displayMemory, drawingMemory, config);

// Video buffer
byte frameBuffer[frameSize];

// Stats
unsigned long frameCount = 0;
unsigned long lastFpsTime = 0;

void setup() {
    Serial.begin(2000000);
    while (!Serial) ;

    leds.begin();
    leds.show();

    Serial.println("Teensy ready for video stream");
    Serial.printf("Expecting frame size: %d bytes\n", frameSize);
}

void loop() {
    if (Serial.available() > 0) {
        int bytesRead = Serial.readBytes(frameBuffer, frameSize);

        if (bytesRead == frameSize) {
            // Update LEDs
            for (int i = 0; i < totalLeds; i++) {
                int bufferIndex = i * 3;
                leds.setPixel(i,
                    frameBuffer[bufferIndex],     // R
                    frameBuffer[bufferIndex + 1], // G
                    frameBuffer[bufferIndex + 2]  // B
                );
            }
            leds.show();

            frameCount++;

            // Calculate and show FPS every second
            unsigned long now = millis();
            if (now - lastFpsTime >= 1000) {
                float fps = frameCount * 1000.0f / (now - lastFpsTime);
                Serial.printf("FPS: %.1f\n", fps);
                frameCount = 0;
                lastFpsTime = now;
            }
        }
    }
}
