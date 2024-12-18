import cv2
import numpy as np
import math
import os

# Video settings
width, height = 400, 960
fps = 30

# Calculate duration based on Pac-Man's movement
pacman_radius = 120
pacman_speed = 6
total_distance = width + 2 * pacman_radius  # Full journey from off-screen to off-screen
duration = total_distance / (pacman_speed * fps)  # Time = Distance / Speed
total_frames = int(fps * duration)

def calculate_x_position(frame):
    progress = frame / total_frames
    return int(-pacman_radius + progress * total_distance)  # Start completely off-screen

# Ensure the output directory exists
output_dir = "../media"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'packman.mp4'), fourcc, fps, (width, height))

# Create a binary file for LED output
binary_output = open(os.path.join(output_dir, 'packman.bin'), 'wb')

# Colors
BLACK = (0, 0, 0)
YELLOW = (0, 255, 255)
BRIGHT_WHITE = (255, 255, 255)  # Bright white for pills

# Pills properties
pill_radius = 20
pill_positions = [120, 240, 360]  # Adjusted X-coordinates of pills

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

def draw_pacman(img, x, y, angle):
    # Draw the main body as an arc
    start_angle = angle
    end_angle = 2 * math.pi - angle
    cv2.ellipse(img, (x, y), (pacman_radius, pacman_radius),
                0, start_angle * 180 / math.pi, end_angle * 180 / math.pi, YELLOW, -1)

    # Draw lines to close the mouth (thicker lines for better visibility)
    mouth_end_1 = (int(x + pacman_radius * math.cos(start_angle)),
                   int(y - pacman_radius * math.sin(start_angle)))
    mouth_end_2 = (int(x + pacman_radius * math.cos(end_angle)),
                   int(y - pacman_radius * math.sin(end_angle)))

    cv2.line(img, (x, y), mouth_end_1, YELLOW, 4)
    cv2.line(img, (x, y), mouth_end_2, YELLOW, 4)

def draw_pill(img, x):
    # Draw pill with a slight glow effect for better visibility
    cv2.circle(img, (x, height // 2), pill_radius + 4, (128, 128, 128), -1)  # Outer glow
    cv2.circle(img, (x, height // 2), pill_radius, BRIGHT_WHITE, -1)         # Inner bright part

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate Pac-Man's position
    pacman_x = calculate_x_position(frame)
    pacman_y = height // 2

    # Only generate frame if Pac-Man is at least partially visible
    if pacman_x >= -pacman_radius and pacman_x <= width + pacman_radius:
        # Calculate mouth angle (oscillating between 0 and pi/4, slower movement)
        mouth_angle = abs(math.pi / 4 * math.sin(frame * 0.2))

        # Draw Pac-Man
        draw_pacman(img, pacman_x, pacman_y, mouth_angle)

        # Draw and check collision with pills
        for pill_x in pill_positions:
            if pacman_x - pacman_radius > pill_x:
                continue  # Pill has been passed, don't draw it
            if abs(pacman_x - pill_x) > pacman_radius:
                draw_pill(img, pill_x)

        # Write the frame to MP4
        out.write(img)

        # Process frame for binary output
        small_frame = cv2.resize(img, (40, 96))
        frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Convert to LAB color space
        lab = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L-channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2,2))
        cl = clahe.apply(l)

        # Merge the CLAHE enhanced L-channel back with A and B channels
        limg = cv2.merge((cl,a,b))

        # Convert back to RGB color space
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)

        # Apply custom contrast and brightness adjustment
        adjusted = adjust_contrast_brightness(enhanced, contrast=1.2, brightness=-10)

        # Apply black threshold
        final = apply_black_threshold(adjusted, threshold=20)

        # Write to binary file
        binary_output.write(final.astype(np.uint8).tobytes())
    elif pacman_x > width + pacman_radius:
        break  # Stop when Pac-Man has completely exited

# Release the VideoWriter and close the binary file
out.release()
binary_output.close()

print(f"Video generated: {os.path.join(output_dir, 'packman.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'packman.bin')}")
