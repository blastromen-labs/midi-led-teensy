import cv2
import numpy as np
import random
import os
import math

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
out = cv2.VideoWriter(os.path.join(output_dir, 'cube_explode.mp4'), fourcc, fps, (width, height))

# Cube properties
cube_size = 40
cube_color = (255, 0, 0)  # Blue (BGR format)
cube_center = (width // 2, height // 2)

# Shake properties
shake_duration = fps  # 1 second of shaking
shake_intensity = 6  # Increased from 3 to 6
shake_frequency = 1.5  # Increased frequency

# Explosion properties
num_particles = 100
particle_color = (0, 255, 255)  # Yellow (BGR format)
particle_size = 2
max_speed = 5

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
    img_glow = cv2.GaussianBlur(img, (7, 7), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: ../videos/cube_explode.mp4")
