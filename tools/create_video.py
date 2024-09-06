import cv2
import numpy as np

# Video settings
width, height = 32, 16
fps = 30
duration = 10  # seconds

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('test_video.mp4', fourcc, fps, (width, height))

# Create a moving circle
radius = 3
x, y = radius, radius
dx, dy = 1, 1

for frame_no in range(fps * duration):
    # Create a black frame
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Draw the circle
    cv2.circle(frame, (x, y), radius, (0, 255, 0), -1)

    # Move the circle
    x += dx
    y += dy

    # Bounce off the edges
    if x <= radius or x >= width - radius:
        dx = -dx
    if y <= radius or y >= height - radius:
        dy = -dy

    # Write the frame
    out.write(frame)

# Release the VideoWriter
out.release()

print("Video generated: test_video.mp4")
