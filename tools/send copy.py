import cv2
import serial
import time

# Configure the serial port
ser = serial.Serial('COM7', 2000000)  # Make sure this matches your Teensy's port

# Open video file
video_path = 'chq.mp4'  # Replace with your video file path
cap = cv2.VideoCapture(video_path)

# Set the capture resolution to match your LED panels
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 32)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 16)

# Get the original video frame rate
fps = cap.get(cv2.CAP_PROP_FPS)

# Handle case where fps is 0, very low, or invalid
if fps <= 0 or not fps:
    print(f"Warning: Invalid FPS ({fps}) detected. Using default.")
    frame_delay = 1 / 30  # Default to 30 fps
else:
    frame_delay = 1 / fps

print(f"Video: {video_path}, FPS: {fps}, Frame delay: {frame_delay}")

while True:
    ret, frame = cap.read()
    if not ret:
        # Restart the video when it ends
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # Ensure the frame is the correct size
    frame = cv2.resize(frame, (32, 16))

    # Convert frame to RGB (OpenCV uses BGR by default)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Flatten the array and ensure it's in the correct order for the LED strips
    led_data = frame_rgb.reshape((-1, 3)).flatten().tobytes()

    # Send the frame data over serial
    ser.write(led_data)
    ser.flush()  # Ensure all data is sent

    # Wait to maintain original video frame rate
    time.sleep(frame_delay)

cap.release()
ser.close()
