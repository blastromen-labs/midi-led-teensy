# MIDI to LED with Teensy 4.1

Code for Teensy 4.1 and OctoWS2811 LED Library (https://www.pjrc.com/teensy/td_libs_OctoWS2811.html) to convert USB MIDI note ON and OFF messages to RGB LED ON and OFF. Current setup:

DAW MIDI Out via USB -> Teensy 4.1 -> OctoWS2811 -> WS2815 (256 or 512 RGB LEDs, 32x8 LED Matrix Display).

Conversation on Teensy forum: https://forum.pjrc.com/index.php?threads/project-midi-to-9000-rgb-leds.75528/#post-347114

## FL Studio MIDI Out

`iCloud Drive/Documents/Image-Line/FL Studio/Presets/Plugin presets/Generators/MIDI Out/Teensy.fst`

## MIDI Mapping

### Channels

LED_MIDI_CHANNEL_LEFT = 1
LED_MIDI_CHANNEL_RIGHT = 2
VIDEO_MIDI_CHANNEL = 3
IMAGE_MIDI_CHANNEL = 4
ROW_MIDI_CHANNEL = 5
STROBE_MIDI_CHANNEL = 6

### CC

HUE = 1
SATURATION = 2
VALUE = 3
X_POSITION = 4
Y_POSITION = 5
VIDEO_DIRECTION = 7
VIDEO_SCALE = 8
VIDEO_SPEED = 10
