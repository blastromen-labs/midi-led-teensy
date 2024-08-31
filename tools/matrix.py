import cv2
import numpy as np
import math

# Video settings
scale_factor = 10
width, height = 32 * scale_factor, 16 * scale_factor
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('rotating_square_hires.mp4', fourcc, fps, (width, height))

# Square properties
square_size = min(width, height) * 0.7
square_color = (0, 255, 0)  # Green color

def rotate_point(x, y, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate rotation angle
    angle = frame * 2 * math.pi / (fps * 5)  # Complete rotation every 5 seconds

    # Define square corners
    half_size = square_size / 2
    corners = [
        (-half_size, -half_size),
        (half_size, -half_size),
        (half_size, half_size),
        (-half_size, half_size)
    ]

    # Rotate and draw the square
    rotated_corners = [rotate_point(x, y, angle) for x, y in corners]
    points = np.array([(int(x + width/2), int(y + height/2)) for x, y in rotated_corners], np.int32)
    points = points.reshape((-1, 1, 2))
    cv2.polylines(img, [points], True, square_color, thickness=scale_factor//2)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: rotating_square_hires.mp4")
