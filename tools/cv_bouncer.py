import cv2
import numpy as np
import random
import os

# Video settings
width, height = 320, 160  # 10 times larger than 32x16
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../videos"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'ball.mp4'), fourcc, fps, (width, height))

# Ball properties
ball_radius = 10
ball_color = (255, 0, 0)  # Blue (BGR format)
ball_x = width // 2
ball_y = height // 2
ball_speed_x = random.choice([-12, 12])  # Slowed down from 20 to 12
ball_speed_y = random.choice([-12, 12])

# Edge flash properties
edge_flash_duration = 5  # frames
edge_flash_color = (255, 0, 255)  # Bright purple (BGR format)
edge_flash_length = 80  # Increased from 40 to 80
edge_flash_width = 4  # Increased from 2 to 4

# Initialize edge flash counters and positions
left_flash = 0
right_flash = 0
top_flash = 0
bottom_flash = 0
left_flash_pos = 0
right_flash_pos = 0
top_flash_pos = 0
bottom_flash_pos = 0

def draw_glow(img, start, end, color, intensity=0.5):
    mask = np.zeros(img.shape[:2], dtype=np.float32)
    cv2.line(mask, start, end, 1, edge_flash_width * 2)
    mask = cv2.GaussianBlur(mask, (0, 0), edge_flash_width // 2)
    mask = mask * intensity
    glow = np.zeros_like(img, dtype=np.float32)
    glow[:] = color
    img[:] = img * (1 - mask[:, :, np.newaxis]) + glow * mask[:, :, np.newaxis]

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Update ball position
    ball_x += ball_speed_x
    ball_y += ball_speed_y

    # Check for collisions with edges
    if ball_x - ball_radius <= 0:
        ball_speed_x = abs(ball_speed_x)
        left_flash = edge_flash_duration
        left_flash_pos = max(0, min(ball_y - edge_flash_length // 2, height - edge_flash_length))
    elif ball_x + ball_radius >= width - 1:
        ball_speed_x = -abs(ball_speed_x)
        right_flash = edge_flash_duration
        right_flash_pos = max(0, min(ball_y - edge_flash_length // 2, height - edge_flash_length))

    if ball_y - ball_radius <= 0:
        ball_speed_y = abs(ball_speed_y)
        top_flash = edge_flash_duration
        top_flash_pos = max(0, min(ball_x - edge_flash_length // 2, width - edge_flash_length))
    elif ball_y + ball_radius >= height - 1:
        ball_speed_y = -abs(ball_speed_y)
        bottom_flash = edge_flash_duration
        bottom_flash_pos = max(0, min(ball_x - edge_flash_length // 2, width - edge_flash_length))

    # Draw flashing edges with glow
    if left_flash > 0:
        draw_glow(img, (0, left_flash_pos), (0, left_flash_pos + edge_flash_length), edge_flash_color)
        left_flash -= 1
    if right_flash > 0:
        draw_glow(img, (width-1, right_flash_pos), (width-1, right_flash_pos + edge_flash_length), edge_flash_color)
        right_flash -= 1
    if top_flash > 0:
        draw_glow(img, (top_flash_pos, 0), (top_flash_pos + edge_flash_length, 0), edge_flash_color)
        top_flash -= 1
    if bottom_flash > 0:
        draw_glow(img, (bottom_flash_pos, height-1), (bottom_flash_pos + edge_flash_length, height-1), edge_flash_color)
        bottom_flash -= 1

    # Draw the ball
    cv2.circle(img, (int(ball_x), int(ball_y)), ball_radius, ball_color, -1)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: ../videos/ball.mp4")
