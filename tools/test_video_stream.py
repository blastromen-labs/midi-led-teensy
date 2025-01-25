import cv2
import serial
import time
import numpy as np

def create_test_pattern(width, height, frame_count):
    # Create a more interesting test pattern
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Moving gradient
    for y in range(height):
        color = (
            (np.sin(y/30 + frame_count/10) + 1) * 127,
            (np.cos(y/20 + frame_count/15) + 1) * 127,
            (np.sin(y/40 + frame_count/20) + 1) * 127
        )
        frame[y, :] = color

    return frame

def test_stream(port='/dev/cu.usbmodem144533101', baud_rate=2000000):
    print(f"Opening serial port {port} at {baud_rate} baud...")
    ser = serial.Serial(port, baud_rate)
    time.sleep(2)
    print("Serial port opened")

    width, height = 40, 96
    chunk_size = 1024
    target_fps = 30
    frame_time = 1.0 / target_fps

    print(f"Streaming {width}x{height} @ {target_fps}fps")
    frame_count = 0
    last_time = time.time()
    fps_timer = time.time()

    try:
        while True:
            current_time = time.time()

            # Create test pattern
            frame = create_test_pattern(width, height, frame_count)

            # Convert and send frame
            frame_bytes = frame.tobytes()
            for i in range(0, len(frame_bytes), chunk_size):
                chunk = frame_bytes[i:i + chunk_size]
                ser.write(chunk)
                time.sleep(0.001)  # Small delay between chunks

            frame_count += 1

            # FPS calculation and display
            if current_time - fps_timer >= 1.0:
                fps = frame_count / (current_time - fps_timer)
                print(f"FPS: {fps:.1f}")
                frame_count = 0
                fps_timer = current_time

            # Frame rate control
            elapsed = time.time() - last_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
            last_time = time.time()

    except KeyboardInterrupt:
        print("\nStream stopped by user")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        ser.close()
        print("Stream ended")

if __name__ == "__main__":
    test_stream()
