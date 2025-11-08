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

| CC  | Function        | Channel | Description                                          |
| --- | --------------- | ------- | ---------------------------------------------------- |
| 1   | HUE             | All     | Hue adjustment (0-127)                               |
| 2   | SATURATION      | All     | Saturation adjustment (0-127)                        |
| 3   | VALUE           | All     | Value/brightness adjustment (0-127)                  |
| 4   | X_POSITION      | 3, 4    | X offset for video/image layers                      |
| 5   | Y_POSITION      | 3, 4    | Y offset for video/image layers                      |
| 7   | VIDEO_DIRECTION | 3       | Video direction (127=reversed)                       |
| 8   | VIDEO_SCALE     | 3, 4    | Video/image scale (64=1x, <64 zoom out, >64 zoom in) |
| 10  | VIDEO_SPEED     | 3       | Video playback speed (64=normal, 0=pause)            |
| 12  | VIDEO_MIRROR    | 3       | Horizontal mirror (127=mirrored)                     |
| 20  | BANK_SELECT     | 3, 4    | Select video/image bank (0-127)                      |

## Bank System

The system supports multiple banks for organizing videos and images. Each bank can contain up to 128 different media files mapped to MIDI notes 0-127.

### Selecting Banks

- **Video Bank**: Send CC 20 on channel 3 with value 0-127
- **Image Bank**: Send CC 20 on channel 4 with value 0-127
- Default bank is 0 for both video and images
- Bank selection uses the same CC (20) on different channels

### File Structure

SD card root structure:

```
/
├── video_map.txt           # Video mapping file
├── image_map.txt           # Image mapping file
├── video/                  # Video files directory
│   ├── 0/                  # Bank 0 videos
│   │   ├── atom.bin
│   │   ├── cube.bin
│   │   └── matrix.bin
│   ├── 1/                  # Bank 1 videos
│   │   ├── helix.bin
│   │   └── planet.bin
│   ├── 2/                  # Bank 2 videos
│   │   └── ...
│   └── ...
└── image/                  # Image files directory
    ├── 0/                  # Bank 0 images
    │   ├── logo.bin
    │   └── pattern1.bin
    ├── 1/                  # Bank 1 images
    │   ├── pattern2.bin
    │   └── graphic.bin
    └── ...
```

### Map File Format

Both `video_map.txt` and `image_map.txt` use the format:

```
MIDI_NOTE,BANK_NUMBER,FILE_NAME
```

Example `video_map.txt`:
```
127,0,atom.bin
126,0,cube.bin
125,0,matrix.bin
127,1,helix.bin
126,1,planet.bin
60,0,dance.bin
60,1,spin.bin
60,2,city.bin
```

Example `image_map.txt`:
```
127,0,logo.bin
126,0,pattern1.bin
127,1,pattern2.bin
126,1,graphic.bin
```

### Usage Example

1. **Select video bank 1**: Send CC 20 with value 1 on channel 3
2. **Play video from bank 1**: Send note-on for note 127 on channel 3
3. **Select image bank 2**: Send CC 20 with value 2 on channel 4
4. **Display image from bank 2**: Send note-on for note 127 on channel 4
