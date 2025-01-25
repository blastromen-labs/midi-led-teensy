import serial
import time
import argparse

def stream_bin_file(filename, port='/dev/cu.usbmodem144533101', baud_rate=2000000):
    # Open serial connection
    print(f"Opening serial port {port} at {baud_rate} baud...")
    ser = serial.Serial(port, baud_rate)
    time.sleep(2)
    print("Serial connection established")

    # Open binary file
    print(f"Opening binary file: {filename}")
    with open(filename, 'rb') as f:
        # Get file size
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        f.seek(0)  # Back to start

        frame_size = 40 * 96 * 3  # width * height * RGB
        total_frames = file_size // frame_size

        print(f"File size: {file_size} bytes")
        print(f"Frame size: {frame_size} bytes")
        print(f"Total frames: {total_frames}")

        chunk_size = 1024  # Send in 1KB chunks
        frame_count = 0
        target_fps = 30
        frame_time = 1.0 / target_fps

        print("Starting stream...")
        last_time = time.time()
        fps_timer = time.time()

        try:
            while True:
                current_time = time.time()

                # Read one frame
                frame_data = f.read(frame_size)
                if not frame_data or len(frame_data) < frame_size:
                    print("Reached end of file, rewinding...")
                    f.seek(0)
                    frame_data = f.read(frame_size)

                # Send frame in chunks
                for i in range(0, len(frame_data), chunk_size):
                    chunk = frame_data[i:i + chunk_size]
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

def main():
    parser = argparse.ArgumentParser(description='Stream binary video file to LED panel')
    parser.add_argument('file', help='Binary file to stream')
    parser.add_argument('--port', default='/dev/cu.usbmodem144533101', help='Serial port')
    parser.add_argument('--baud', type=int, default=2000000, help='Baud rate')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS')
    args = parser.parse_args()

    stream_bin_file(args.file, args.port, args.baud)

if __name__ == "__main__":
    main()
