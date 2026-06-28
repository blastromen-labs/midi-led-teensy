# MIDI to LED with Teensy 4.1

Firmware for Teensy 4.1 that drives a large WS2811 matrix from USB MIDI — block colors, full-row fills, SD-card video/image layers, strobe patterns, and optional serial video streaming.

**Signal chain:** DAW / controller → USB MIDI → Teensy 4.1 → OctoWS2811 → WS2811 matrix (40×96 logical pixels, 3,840 LEDs)

- [OctoWS2811 library](https://www.pjrc.com/teensy/td_libs_OctoWS2811.html)
- [Teensy forum thread](https://forum.pjrc.com/index.php?threads/project-midi-to-9000-rgb-leds.75528/#post-347114)
- **[Software architecture report](docs/architecture.html)** — open in a browser for diagrams, module map, and data-flow

---

## For AI agents and contributors

This section is for humans and Cursor agents working on the repo.

### Where to edit

| Goal | Location |
|------|----------|
| Firmware features, MIDI, compositing | [`src/latest.ino`](src/latest.ino) only |
| USB product name | [`src/name.c`](src/name.c) |
| Convert video/image to `.bin` | [`tools/`](tools/) (Python, off-device) |
| Architecture documentation | [`docs/architecture.html`](docs/architecture.html) |

**Default:** keep all firmware in `src/latest.ino`. The file is organized into labeled sections (`// === Configuration ===`, etc.). Add helpers in the utilities section; do not split into new tabs unless asked.

### Repository layout

```
midi-led-teensy/
├── src/
│   ├── latest.ino      # Main firmware (single source of truth)
│   └── name.c          # USB name ("TEENSY1")
├── docs/
│   └── architecture.html
├── tools/              # Media conversion & serial streaming scripts
├── old-teensy-projects/  # Archived sketches — do not use as source of truth
└── .cursor/rules/
    └── midi-teensy-main.mdc   # Cursor agent conventions
```

### Architecture at a glance

```
MIDI (usbMIDI) ──► dispatchNoteEvent ──► channel handlers ──► global state
                                                              │
SD video ──► frameBuffer ─────────────────────────────────────┤
Serial stream ──► frameBuffer (fast path, bypasses layers)    │
                                                              ▼
                                                    updateLEDs() compositor
                                                              │
                                                    OctoWS2811 → physical LEDs
```

**Compositing order** (bottom → top): video → image (alpha blend) → LED blocks → strobe overlay.

See [`docs/architecture.html`](docs/architecture.html) for full detail.

### Conventions

- **C++ standard:** **C++17 max** (Teensyduino / Arduino toolchain). Do not use C++20 features (`std::span`, concepts, `consteval`, etc.)
- **Constants:** display size derived from `width` / `height`; frame size is `FRAME_BYTES = width * height * 3`
- **Types:** `LedColor`, `Mapping`, `HSVAdjustments`, `Region` — reuse instead of duplicating structs
- **Helpers:** `sampleLayer`, `findMapping`, `mapCCScale`, `setGroupColor`, `buildMediaPath`, etc.
- **MIDI dispatch:** all note on/off goes through `dispatchNoteEvent()` in `setup()`
- **Refresh:** handlers set `ledStateChanged`; `loop()` calls `updateLEDs()` + `leds.show()` when dirty

### Intentional behaviors (don't "fix" without discussion)

| Behavior | Why |
|----------|-----|
| Serial video writes pixels directly | Fast path for 2 Mbaud streaming; bypasses HSV/layers |
| `handleSerialVideo` takes priority over SD | Live stream overrides card playback |
| Equal R=G=B in `groupStates` | Legacy strobe shortcut still reachable from block MIDI |
| Per-channel HSV on LED blocks | Blue/red/green blocks stay independent when color-shifted |

### Build and flash

1. Open `src/latest.ino` in Arduino IDE or Teensyduino
2. Board: **Teensy 4.1**
3. **C++17** is the highest supported language standard — avoid C++20 syntax and library features
4. Libraries: **OctoWS2811**, **FastLED**, **SD** (Teensy core)
5. Upload; SD card must contain map files and media (see below)

There is no CI or automated test suite — validation is on hardware.

### Smoke test checklist (after firmware changes)

1. Startup: first 768 LEDs flash blue × 3
2. MIDI ch 1/2: block notes, independent B/R/G
3. MIDI ch 5: horizontal row bands
4. MIDI ch 6: strobe patterns + white rows (notes 103–114)
5. MIDI ch 3: SD video — play, loop, speed, reverse, scale, mirror, bank CC 20
6. MIDI ch 4: image on/off, scale, HSV, alpha over video
7. Serial: frame stream at 2 Mbaud; 1 s timeout clears screen and SD resumes

### Adding a feature (typical workflow)

1. Read [`docs/architecture.html`](docs/architecture.html) and the relevant section in `latest.ino`
2. Add constants/types near the top; helpers in utility sections
3. Wire MIDI in the appropriate `handle*Event` or `handleControlChange`
4. If compositing changes, update `updateLEDs()` layer order carefully
5. Update this README (MIDI tables) if channels/CCs change
6. Suggest the smoke test items above

---

## FL Studio MIDI Out

`iCloud Drive/Documents/Image-Line/FL Studio/Presets/Plugin presets/Generators/MIDI Out/Teensy.fst`

---

## MIDI mapping

### Channels

| Channel | Constant | Function |
| ------- | -------- | -------- |
| 1 | `LED_MIDI_CHANNEL_LEFT` | Block RGB — columns 1–3 |
| 2 | `LED_MIDI_CHANNEL_RIGHT` | Block RGB — columns 4–5 |
| 3 | `VIDEO_MIDI_CHANNEL` | SD video trigger + video CCs |
| 4 | `IMAGE_MIDI_CHANNEL` | SD image trigger + image CCs |
| 5 | `ROW_MIDI_CHANNEL` | Full-width row fill (8 px bands) |
| 6 | `STROBE_MIDI_CHANNEL` | Region strobe + white row strobe |

### Control changes

| CC | Constant | Channel | Description |
| -- | -------- | ------- | ----------- |
| 1 | `HUE_CC` | 1–6 (context) | Hue (0–127 → scaled) |
| 2 | `SATURATION_CC` | 1–6 (context) | Saturation |
| 3 | `VALUE_CC` | 1–6 (context) | Value / brightness |
| 4 | `X_POSITION_CC` | 3, 4 | X offset (64 = center) |
| 5 | `Y_POSITION_CC` | 3, 4 | Y offset (64 = center) |
| 7 | `VIDEO_DIRECTION_CC` | 3 | 127 = reverse playback |
| 8 | `VIDEO_SCALE_CC` | 3, 4 | Scale (64 = 1×) |
| 10 | `VIDEO_SPEED_CC` | 3 | Speed (64 = normal, 0 = pause) |
| 12 | `VIDEO_MIRROR_CC` | 3 | 127 = horizontal mirror |
| 20 | `BANK_CC` | 3, 4 | Bank select 0–127 |

---

## Bank system

Multiple banks organize videos and images. Each bank maps MIDI notes 0–127 to files via map files on the SD card.

### Selecting banks

- **Video:** CC 20 on channel 3 (value 0–127)
- **Image:** CC 20 on channel 4 (value 0–127)
- Default bank: **0**
- CC and note-on can be sent in the same tick — bank is applied before lookup

### SD card layout

```
/
├── video_map.txt
├── image_map.txt
├── video/
│   ├── 0/
│   │   ├── atom.bin
│   │   └── cube.bin
│   └── 1/
│       └── helix.bin
└── image/
    ├── 0/
    │   └── logo.bin
    └── 1/
        └── pattern.bin
```

Each `.bin` video frame or image is raw RGB, **11,520 bytes** (`40 × 96 × 3`).

### Map file format

`video_map.txt` and `image_map.txt`:

```
MIDI_NOTE,BANK_NUMBER,FILE_NAME
```

**Filename length:** names must fit **8.3** format (max 8 characters + dot + 3-character extension, e.g. `helix.bin`, `pattern1.bin`). The firmware stores filenames in a 12-character + null buffer (`char filename[13]` in `Mapping`). Longer names are truncated when maps are loaded and will not match files on the SD card.

Example `video_map.txt`:

```
127,0,atom.bin
126,0,cube.bin
127,1,helix.bin
60,0,dance.bin
60,1,spin.bin
```

Example `image_map.txt`:

```
127,0,logo.bin
126,0,pattern1.bin
127,1,pattern2.bin
```

### Usage example

1. Select video bank 1: CC 20 = 1 on channel 3
2. Play video: note-on 127 on channel 3
3. Select image bank 2: CC 20 = 2 on channel 4
4. Show image: note-on 127 on channel 4

---

## Tools

Python scripts in [`tools/`](tools/) prepare media for the device (not part of firmware):

| Script | Purpose |
|--------|---------|
| `convert.py`, `convert_vid.py`, `convert_img.py` | Image/video → `.bin` |
| `video_stream.py`, `send.py` | Stream frames over serial |
| `streamer/` | Web UI for streaming |
| `cv_*.py`, `cube.py` | Generative content |
