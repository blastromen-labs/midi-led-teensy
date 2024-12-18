import cv2
import numpy as np
import math
import os

# Video settings
width, height = 400, 960
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../media"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'matrix.mp4'), fourcc, fps, (width, height))

# Create a binary file for LED output
binary_output = open(os.path.join(output_dir, 'matrix.bin'), 'wb')

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

# Grid properties
grid_color = (0, 255, 0)  # Green color
horizon_y = height // 3  # Horizon line position
num_vertical_lines = 20
num_horizontal_lines = 15
line_thickness = 2

def draw_perspective_grid(img, offset, zoom):
    # Draw vertical lines
    for i in range(-num_vertical_lines//2, num_vertical_lines//2 + 1):
        x = width//2 + i * (width//num_vertical_lines)
        x = int(x + offset % (width//num_vertical_lines))

        # Calculate vanishing point
        vanishing_x = width//2
        vanishing_y = horizon_y

        # Draw line from bottom to horizon with zoom effect
        bottom_x = int(vanishing_x + (x - vanishing_x) * (1/zoom))
        cv2.line(img, (x, height), (bottom_x, horizon_y), grid_color, line_thickness)

    # Draw horizontal lines with increasing density as we zoom
    num_lines = int(num_horizontal_lines * zoom)
    for i in range(num_lines):
        y = height - i * (height - horizon_y)//num_lines
        y = int(y)

        # Calculate perspective points for horizontal lines
        left_x = int(width//2 - (width * (1/zoom) * (y - horizon_y)/(height - horizon_y)))
        right_x = int(width//2 + (width * (1/zoom) * (y - horizon_y)/(height - horizon_y)))

        cv2.line(img, (left_x, y), (right_x, y), grid_color, line_thickness)

    # Add some mountains on the horizon with zoom effect
    mountain_points = []
    for i in range(10):
        x = width * i / 9
        y = horizon_y - (50/zoom) * math.sin(i * math.pi / 4 + offset/100)
        mountain_points.append([int(x), int(y)])

    mountain_points = np.array(mountain_points)
    cv2.polylines(img, [mountain_points], False, grid_color, line_thickness)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate zoom and offset
    t = frame / total_frames
    zoom = 1 + t * 5  # Continuous zoom in
    offset = frame * (5 + t * 10)  # Accelerating movement

    # Draw the grid
    draw_perspective_grid(img, offset, zoom)

    # Add sun with zoom effect
    sun_radius = int(30 / (zoom * 0.5))  # Sun gets smaller as we zoom in
    sun_x = width // 2
    sun_y = horizon_y - int(50 / zoom)
    if sun_radius > 0:  # Only draw sun if it's still visible
        cv2.circle(img, (sun_x, sun_y), sun_radius, grid_color, -1)

    # Add glow effect
    img_glow = cv2.GaussianBlur(img, (15, 15), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

    # Write the frame to MP4
    out.write(img)

    # Process frame for binary output
    small_frame = cv2.resize(img, (40, 96))
    frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Convert to LAB color space
    lab = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2,2))
    cl = clahe.apply(l)

    # Merge channels
    limg = cv2.merge((cl,a,b))

    # Convert back to RGB
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)

    # Adjust contrast and brightness
    adjusted = adjust_contrast_brightness(enhanced, contrast=1.2, brightness=-10)

    # Apply threshold
    final = apply_black_threshold(adjusted, threshold=20)

    # Write to binary file
    binary_output.write(final.astype(np.uint8).tobytes())

# Release everything
out.release()
binary_output.close()

print(f"Video generated: {os.path.join(output_dir, 'matrix.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'matrix.bin')}")
