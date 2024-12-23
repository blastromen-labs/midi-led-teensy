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
horizon_y = height // 2    # Centered horizon
line_thickness = 2
num_diagonals = 8        # Number of diagonal lines
num_dots = 8            # Reduced number of dots per line (was 15)
dot_size = 3            # Base size for dots

def draw_wireframe_landscape(img, offset):
    # Draw horizon line (very dark)
    cv2.line(img, (0, horizon_y), (width, horizon_y), (0, 20, 0), line_thickness)

    # Draw diagonal lines made of dots
    center_x = width // 2

    # Calculate dot positions for each diagonal line
    for i in range(num_diagonals // 2):
        progress = i / (num_diagonals / 2)
        spacing = math.pow(progress, 1.5)  # Non-linear progression

        # Calculate points along each diagonal line
        for j in range(num_dots):
            # Calculate dot position along the line with movement (reduced speed)
            dot_progress = ((j + (offset / 35)) % num_dots) / num_dots  # Slower speed (was 25)

            # All dots start from center point
            start_x = center_x
            start_y = horizon_y

            # Calculate end points
            end_x_left = 0
            end_x_right = width
            end_y = horizon_y + ((height - horizon_y) * spacing)

            # Interpolate dot positions from center
            x1 = int(start_x + (end_x_left - start_x) * dot_progress)
            x2 = int(start_x + (end_x_right - start_x) * dot_progress)
            y = int(start_y + (end_y - start_y) * dot_progress)

            # Calculate brightness based on distance from center
            brightness = math.pow(dot_progress, 0.7)  # More dramatic brightness curve
            color = (0, int(20 + 235 * brightness), 0)  # Green from 20 to 255

            # Calculate dot size based on distance (larger as they get further)
            current_dot_size = int(dot_size + (dot_size * 2 * dot_progress))

            # Draw dots
            cv2.circle(img, (x1, y), current_dot_size, color, -1)
            cv2.circle(img, (x2, y), current_dot_size, color, -1)

    # Draw center line dots
    for j in range(num_dots):
        # Calculate dot position along center line with movement (reduced speed)
        dot_progress = ((j + (offset / 35)) % num_dots) / num_dots  # Slower speed (was 25)

        # Calculate y position
        y = int(horizon_y + (height - horizon_y) * dot_progress)

        # Calculate brightness and size
        brightness = math.pow(dot_progress, 0.7)
        color = (0, int(20 + 235 * brightness), 0)
        current_dot_size = int(dot_size + (dot_size * 2 * dot_progress))

        # Draw center dot
        cv2.circle(img, (center_x, y), current_dot_size, color, -1)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate movement with floating point precision (reduced speed)
    offset = frame * 4.0  # Reduced speed (was 6.0)

    # Draw the wireframe landscape
    draw_wireframe_landscape(img, offset)

    # Add glow effect
    glow = cv2.GaussianBlur(img, (7, 7), 0)
    img = cv2.addWeighted(img, 1, glow, 0.4, 0)

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

    # Apply black threshold
    final = apply_black_threshold(adjusted, threshold=20)

    # Write to binary file
    binary_output.write(final.astype(np.uint8).tobytes())

# Release everything
out.release()
binary_output.close()

print(f"Video generated: {os.path.join(output_dir, 'matrix.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'matrix.bin')}")
