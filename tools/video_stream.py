import cv2
import serial
import time
import numpy as np
import argparse
import os
import warnings

# Suppress macOS camera warnings
os.environ['OPENCV_VIDEOIO_MACH_NEW_API'] = '0'
warnings.filterwarnings('ignore', category=DeprecationWarning)

class VideoStreamer:
    def __init__(self, port='/dev/cu.usbmodem144533101', baud_rate=2000000, width=40, height=96):
        self.width = width
        self.height = height
        self.frame_size = width * height * 3
        self.chunk_size = 1024  # Send in 1KB chunks

        # Open serial connection
        print(f"Opening serial port {port} at {baud_rate} baud...")
        self.ser = serial.Serial(port, baud_rate)
        time.sleep(2)  # Wait for connection to establish
        print("Serial connection established")

    def stream_video(self, source):
        # Open video source (0 for webcam, or file path)
        print(f"Opening video source: {source}")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("Error: Could not open video source")
            return

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"Video properties - FPS: {fps}, Total frames: {total_frames}")

        target_fps = 30
        frame_time = 1.0 / target_fps

        print("Starting video stream...")
        frame_count = 0
        last_time = time.time()
        fps_timer = time.time()

        try:
            while True:
                current_time = time.time()
                ret, frame = cap.read()

                if not ret:
                    if isinstance(source, str):  # If it's a file, rewind
                        print("Reached end of video, rewinding...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        print("Failed to read frame from webcam")
                        break

                # Resize to panel dimensions
                frame = cv2.resize(frame, (self.width, self.height))

                # Convert to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Show preview
                preview = cv2.resize(frame, (self.width * 4, self.height * 4))
                cv2.imshow('Preview', preview)

                # Send frame in chunks
                frame_bytes = frame.tobytes()
                for i in range(0, len(frame_bytes), self.chunk_size):
                    chunk = frame_bytes[i:i + self.chunk_size]
                    self.ser.write(chunk)
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

                # Check for quit command
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Quit command received")
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.ser.close()
            print("Stream ended")

def main():
    parser = argparse.ArgumentParser(description='Stream video to LED panel')
    parser.add_argument('--port', default='/dev/cu.usbmodem144533101', help='Serial port')
    parser.add_argument('--source', default='0', help='Video source (0 for webcam, or path to video file)')
    parser.add_argument('--baud', type=int, default=2000000, help='Baud rate')
    args = parser.parse_args()

    # Convert source to int if it's a webcam index
    source = args.source
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    streamer = VideoStreamer(port=args.port, baud_rate=args.baud)
    streamer.stream_video(source)

if __name__ == "__main__":
    main()
