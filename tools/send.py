import cv2
import serial
import time
import mido
import os
import threading
import numpy as np

# Configure the serial port
ser = serial.Serial('COM7', 2000000)  # Make sure this matches your Teensy's port

print(mido.get_input_names())
# Configure MIDI input
midi_port = mido.open_input('port0 1')  # Replace with your MIDI port name

# Video paths
video_folder = '../videos/'
video_files = {
    127: 'chq.mp4',
    126: 'a.mp4',
    125: 'rr.mp4',
    124: 'hii.mp4',
    123: 'hand.mp4',
    122: 'termi.mp4',
}

# Global variables to control video playback
current_video_thread = None
video_playing = False
current_note = None

def clear_led_panel():
    # Create a black frame
    black_frame = np.zeros((16, 32, 3), dtype=np.uint8)
    led_data = black_frame.reshape((-1, 3)).flatten().tobytes()
    ser.write(led_data)
    ser.flush()
    print("LED panel cleared")

def play_video(video_path):
    global video_playing, current_note
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 32)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 16)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Handle case where fps is 0, very low, or invalid
    if fps <= 0 or not fps:
        print(f"Warning: Invalid FPS ({fps}) detected. Using default.")
        frame_delay = 1 / 30  # Default to 30 fps
    else:
        frame_delay = 1 / fps

    print(f"Video: {video_path}, FPS: {fps}, Frame delay: {frame_delay}")

    while video_playing:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (32, 16))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        led_data = frame_rgb.reshape((-1, 3)).flatten().tobytes()

        ser.write(led_data)
        ser.flush()

        time.sleep(frame_delay)

    cap.release()
    print("Video playback stopped")

def handle_midi():
    global video_playing, current_video_thread, current_note
    for msg in midi_port.iter_pending():
        print(msg)
        if msg.type == 'note_on':
            if msg.note in video_files:
                # Stop current video if playing
                if video_playing:
                    video_playing = False
                    if current_video_thread:
                        current_video_thread.join()

                # Start new video
                print(f"Starting video for note {msg.note}")
                video_path = os.path.join(video_folder, video_files[msg.note])
                video_playing = True
                current_note = msg.note
                current_video_thread = threading.Thread(target=play_video, args=(video_path,), daemon=True)
                current_video_thread.start()

        elif msg.type == 'note_off':
            if msg.note == current_note:
                print(f"Stopping video for note {msg.note}")
                video_playing = False
                if current_video_thread:
                    current_video_thread.join()
                current_note = None
                clear_led_panel()

try:
    print("Waiting for MIDI messages...")
    while True:
        handle_midi()
        time.sleep(0.001)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    pass
finally:
    video_playing = False
    if current_video_thread:
        current_video_thread.join()
    clear_led_panel()
    ser.close()
    midi_port.close()
