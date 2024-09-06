import cv2
import numpy as np
import math
import os

# Video settings
width, height = 320, 160
fps = 30
duration = 5  # seconds
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../videos"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'packman.mp4'), fourcc, fps, (width, height))

# Colors
BLACK = (0, 0, 0)
YELLOW = (0, 255, 255)
BRIGHT_WHITE = (255, 255, 255)  # Bright white for pills

# Pac-Man properties
pacman_radius = 50
pacman_speed = 4  # Increased from 2 to 4 pixels per frame

# Pills properties
pill_radius = 6
pill_positions = [80, 160, 240]  # X-coordinates of pills

def draw_pacman(img, x, y, angle):
    # Draw the main body as an arc
    start_angle = angle
    end_angle = 2 * math.pi - angle
    cv2.ellipse(img, (x, y), (pacman_radius, pacman_radius),
                0, start_angle * 180 / math.pi, end_angle * 180 / math.pi, YELLOW, -1)

    # Draw lines to close the mouth
    mouth_end_1 = (int(x + pacman_radius * math.cos(start_angle)),
                   int(y - pacman_radius * math.sin(start_angle)))
    mouth_end_2 = (int(x + pacman_radius * math.cos(end_angle)),
                   int(y - pacman_radius * math.sin(end_angle)))

    cv2.line(img, (x, y), mouth_end_1, YELLOW, 2)
    cv2.line(img, (x, y), mouth_end_2, YELLOW, 2)

def draw_pill(img, x):
    cv2.circle(img, (x, height // 2), pill_radius, BRIGHT_WHITE, -1)

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate Pac-Man's position
    pacman_x = int((frame * pacman_speed) % (width + 2 * pacman_radius) - pacman_radius)
    pacman_y = height // 2

    # Calculate mouth angle (oscillating between 0 and pi/6, slower movement)
    mouth_angle = abs(math.pi / 6 * math.sin(frame * 0.3))

    # Draw Pac-Man
    draw_pacman(img, pacman_x, pacman_y, mouth_angle)

    # Draw and check collision with pills
    for pill_x in pill_positions:
        if pacman_x - pacman_radius > pill_x:
            continue  # Pill has been passed, don't draw it
        if abs(pacman_x - pill_x) > pacman_radius:
            draw_pill(img, pill_x)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: ../videos/packman.mp4")
