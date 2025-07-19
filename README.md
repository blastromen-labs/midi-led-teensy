# MIDI to LED with Teensy 4.1

Code for Teensy 4.1 and OctoWS2811 LED Library (https://www.pjrc.com/teensy/td_libs_OctoWS2811.html) to convert USB MIDI note ON and OFF messages to RGB LED ON and OFF. Current setup:

DAW MIDI Out via USB -> Teensy 4.1 -> OctoWS2811 -> WS2815 (256 or 512 RGB LEDs, 32x8 LED Matrix Display).

Conversation on Teensy forum: https://forum.pjrc.com/index.php?threads/project-midi-to-9000-rgb-leds.75528/#post-347114

## FL Studio MIDI Out

`iCloud Drive/Documents/Image-Line/FL Studio/Presets/Plugin presets/Generators/MIDI Out/Teensy.fst`

## MIDI Mapping

### Channels

| Channel | Function               |
| ------- | ---------------------- |
| 1       | LED_MIDI_CHANNEL_LEFT  |
| 2       | LED_MIDI_CHANNEL_RIGHT |
| 3       | VIDEO_MIDI_CHANNEL     |
| 4       | IMAGE_MIDI_CHANNEL     |
| 5       | ROW_MIDI_CHANNEL       |
| 6       | STROBE_MIDI_CHANNEL    |

### CC

| CC  | Function        |
| --- | --------------- |
| 1   | HUE             |
| 2   | SATURATION      |
| 3   | VALUE           |
| 4   | X_POSITION      |
| 5   | Y_POSITION      |
| 7   | VIDEO_DIRECTION |
| 8   | VIDEO_SCALE     |
| 10  | VIDEO_SPEED     |
| 12  | VIDEO_MIRROR    |
