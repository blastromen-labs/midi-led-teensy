import cv2
import numpy as np
import random
import os
import math

# Video settings
width, height = 320, 960
fps = 30
duration = 5  # seconds
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../videos"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'cube_explode.mp4'), fourcc, fps, (width, height))

# Create a binary file for 32x96 output
binary_output = open(os.path.join(output_dir, 'cube_explode.bin'), 'wb')

# Cube properties
cube_size = int(min(width, height) * 0.3)  # Increased size to 30% of the smaller dimension
cube_color = (255, 0, 0)  # Blue (BGR format)
cube_center = (width // 2, height // 2)

# Shake properties
shake_duration = fps  # 1 second of shaking
shake_intensity = 18  # Increased from 6 to 18
shake_frequency = 1.5

# Explosion properties
num_particles = 300  # Increased from 100 to 300
particle_color = (0, 255, 255)  # Yellow (BGR format)
particle_size = 6  # Increased from 2 to 6
max_speed = 15  # Increased from 5 to 15

# Particle class
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-max_speed, max_speed)
        self.vy = random.uniform(-max_speed, max_speed)

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, img):
        cv2.circle(img, (int(self.x), int(self.y)), particle_size, particle_color, -1)

# Create particles
particles = [Particle(cube_center[0], cube_center[1]) for _ in range(num_particles)]

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    if frame < shake_duration:  # Shake the cube for 1 second
        # Calculate shake offset
        shake_offset_x = int(shake_intensity * math.sin(frame * shake_frequency))
        shake_offset_y = int(shake_intensity * math.cos(frame * shake_frequency * 1.2))

        # Draw shaking cube
        half_size = cube_size // 2
        cv2.rectangle(img,
                      (cube_center[0] - half_size + shake_offset_x, cube_center[1] - half_size + shake_offset_y),
                      (cube_center[0] + half_size + shake_offset_x, cube_center[1] + half_size + shake_offset_y),
                      cube_color, -1)
    elif frame < shake_duration + 5:  # Brief pause after shaking
        # Draw static cube
        half_size = cube_size // 2
        cv2.rectangle(img,
                      (cube_center[0] - half_size, cube_center[1] - half_size),
                      (cube_center[0] + half_size, cube_center[1] + half_size),
                      cube_color, -1)
    else:
        # Update and draw particles
        for particle in particles:
            particle.update()
            particle.draw(img)

    # Add some glow to the cube and particles
    img_glow = cv2.GaussianBlur(img, (21, 21), 0)  # Increased blur size
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

    # Write the frame to MP4
    out.write(img)

    # Process frame for binary output
    small_frame = cv2.resize(img, (32, 96))
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
    adjusted = adjust_contrast_brightness(enhanced, contrast=0.9, brightness=-20)

    # Apply black threshold
    final = apply_black_threshold(adjusted, threshold=20)

    # Write to binary file
    binary_output.write(final.astype(np.uint8).tobytes())

# Release the VideoWriter and close the binary file
out.release()
binary_output.close()

print(f"Video generated: {os.path.join(output_dir, 'cube_explode.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'cube_explode.bin')}")
