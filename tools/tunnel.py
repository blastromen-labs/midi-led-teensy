import cv2
import numpy as np
import math
import os

# Video settings
width, height = 320, 160
fps = 30
duration = 30  # seconds (increased from 10 to 30)
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../videos"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'infinite_tunnel.mp4'), fourcc, fps, (width, height))

# Tunnel properties
tunnel_segments = 16
tunnel_rings = 30  # Increased from 20 to 30
tunnel_radius = 100
tunnel_length = 1000  # Increased from 500 to 1000
tunnel_color = (255, 255, 0)  # Cyan in BGR
speed = 20  # Speed of movement through the tunnel

def draw_tunnel(img, offset):
    for i in range(tunnel_rings):
        z = i * (tunnel_length / tunnel_rings) - offset
        t = z / tunnel_length
        radius = tunnel_radius * (1 - t * 0.8)  # Sharper perspective

        for j in range(tunnel_segments):
            angle1 = j * (2 * math.pi / tunnel_segments)
            angle2 = ((j + 1) % tunnel_segments) * (2 * math.pi / tunnel_segments)

            x1 = int(width // 2 + radius * math.cos(angle1))
            y1 = int(height // 2 + radius * math.sin(angle1))
            x2 = int(width // 2 + radius * math.cos(angle2))
            y2 = int(height // 2 + radius * math.sin(angle2))

            cv2.line(img, (x1, y1), (x2, y2), tunnel_color, 1)

            if i > 0:
                prev_z = (i - 1) * (tunnel_length / tunnel_rings) - offset
                prev_t = prev_z / tunnel_length
                prev_radius = tunnel_radius * (1 - prev_t * 0.8)
                prev_x = int(width // 2 + prev_radius * math.cos(angle1))
                prev_y = int(height // 2 + prev_radius * math.sin(angle1))
                cv2.line(img, (x1, y1), (prev_x, prev_y), tunnel_color, 1)

def draw_triangle(img, pt1, pt2, pt3, color, thickness=1):
    if thickness > 0:
        cv2.line(img, pt1, pt2, color, thickness)
        cv2.line(img, pt2, pt3, color, thickness)
        cv2.line(img, pt3, pt1, color, thickness)
    else:
        pts = np.array([pt1, pt2, pt3], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.fillPoly(img, [pts], color)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate offset
    offset = (frame * speed) % tunnel_length

    # Draw the tunnel
    draw_tunnel(img, offset)

    # Add some glow effect
    img_glow = cv2.GaussianBlur(img, (3, 3), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

    # Add a simple spaceship
    ship_color = (0, 0, 255)  # Red in BGR
    draw_triangle(img,
                  (width//2, height-30),
                  (width//2-15, height-10),
                  (width//2+15, height-10),
                  ship_color, thickness=-1)  # Use -1 for filled triangle

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: ../videos/infinite_tunnel.mp4")