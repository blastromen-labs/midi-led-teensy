import cv2
import numpy as np
import math

# Video settings
width, height = 320, 960
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('synthwave_flying.mp4', fourcc, fps, (width, height))

# Create a binary file for 32x96 output
binary_output = open('synthwave_flying.bin', 'wb')

# Colors
sun_color = (255, 255, 0)  # Yellow
ground_color = (255, 0, 255)  # Magenta
mountain_color = (0, 255, 255)  # Cyan

def draw_sun(img, center, radius):
    cv2.circle(img, center, radius, sun_color, -1)
    for i in range(1, 6):
        cv2.circle(img, center, radius - i*5, (255, 128, 0), 2)

def draw_ground(img, horizon, offset):
    for i in range(20):
        y = horizon + i * 30
        cv2.line(img, (0, y), (width, y), ground_color, 1)
    for i in range(20):
        x = (i * width // 10 + offset) % width
        pt1 = (x, horizon)
        pt2 = (width//2, height)
        cv2.line(img, pt1, pt2, ground_color, 1)

def draw_mountains(img, horizon, offset):
    for i in range(7):
        x1 = ((i-1) * width // 5 + offset) % width
        x2 = (i * width // 5 + offset) % width
        x3 = ((i-0.5) * width // 5 + offset) % width
        pts = np.array([
            [x1, horizon],
            [x2, horizon],
            [x3, horizon - 100 - np.random.randint(50)]
        ], np.int32)
        cv2.fillPoly(img, [pts], mountain_color)
        cv2.polylines(img, [pts], True, (255, 255, 255), 2)

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate movement offset
    offset = int(frame * width / (fps * 2))  # Complete cycle every 2 seconds

    # Draw sun
    sun_y = int(height * 0.3 + 20 * math.sin(frame * 2 * math.pi / total_frames))
    draw_sun(img, (width // 2, sun_y), 100)

    # Draw ground
    horizon = int(height * 0.6)
    draw_ground(img, horizon, offset)

    # Draw mountains
    draw_mountains(img, horizon, offset // 2)  # Mountains move slower for parallax effect

    # Add some stars
    for _ in range(100):
        x = np.random.randint(width)
        y = np.random.randint(horizon)
        img[y, x] = (255, 255, 255)

    # Write the frame to MP4
    out.write(img)

    # Process frame for binary output
    small_frame = cv2.resize(img, (32, 96))
    frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Apply custom contrast and brightness adjustment
    adjusted = adjust_contrast_brightness(frame_rgb, contrast=1.2, brightness=-10)

    # Apply black threshold
    final = apply_black_threshold(adjusted, threshold=20)

    # Write to binary file
    binary_output.write(final.astype(np.uint8).tobytes())

# Release the VideoWriter and close the binary file
out.release()
binary_output.close()

print("Video generated: synthwave_flying.mp4")
print("Binary file generated: synthwave_flying.bin")
