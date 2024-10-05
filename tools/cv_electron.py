import cv2
import numpy as np
import os
import math
import random

# Video settings
width, height = 320, 160
fps = 30
duration = 6  # seconds (increased to accommodate explosion)
total_frames = fps * duration

# Ensure the output directory exists
output_dir = "../media/videos"
os.makedirs(output_dir, exist_ok=True)

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'atom.mp4'), fourcc, fps, (width, height))

# Atom properties
max_atom_size = 200
min_atom_size = 1

# Electron properties
electron_color = (255, 255, 0)  # Cyan (BGR format)
electron_size = 2
max_orbit_radius = 100
min_orbit_radius = 5
base_electron_speed = 0.1

# Trace properties
trace_length = 10

# Explosion properties
explosion_start = int(total_frames * 0.8)  # Start explosion at 80% of the video
num_particles = 100
particle_max_speed = 5

# Create nucleus with rotating red and blue spheres
def create_nucleus(size, angle):
    nucleus = np.zeros((size, size, 3), dtype=np.uint8)
    center = size // 2
    radius = max(1, size // 4)  # Ensure radius is at least 1

    # Calculate positions of red and blue spheres
    x1 = int(center + radius * math.cos(angle))
    y1 = int(center + radius * math.sin(angle))
    x2 = int(center - radius * math.cos(angle))
    y2 = int(center - radius * math.sin(angle))

    # Draw red sphere
    cv2.circle(nucleus, (x1, y1), radius, (0, 0, 255), -1)
    cv2.circle(nucleus, (x1, y1), radius, (0, 0, 200), 2)  # Darker outline

    # Draw blue sphere
    cv2.circle(nucleus, (x2, y2), radius, (255, 0, 0), -1)
    cv2.circle(nucleus, (x2, y2), radius, (200, 0, 0), 2)  # Darker outline

    # Add shading to create 3D effect
    Y, X = np.ogrid[:size, :size]
    dist_from_center1 = np.sqrt((X - x1)**2 + (Y - y1)**2)
    dist_from_center2 = np.sqrt((X - x2)**2 + (Y - y2)**2)

    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        shading1 = np.where(dist_from_center1 != 0, np.clip(1 - dist_from_center1 / radius, 0, 1), 1)
        shading2 = np.where(dist_from_center2 != 0, np.clip(1 - dist_from_center2 / radius, 0, 1), 1)

    nucleus[:,:,2] = np.maximum(nucleus[:,:,2], (shading1 * 255).astype(np.uint8))  # Red sphere
    nucleus[:,:,0] = np.maximum(nucleus[:,:,0], (shading2 * 255).astype(np.uint8))  # Blue sphere

    return cv2.GaussianBlur(nucleus, (3, 3), 0)

# Create explosion particles
particles = []
for _ in range(num_particles):
    particle = {
        'x': width // 2,
        'y': height // 2,
        'vx': random.uniform(-1, 1) * particle_max_speed,
        'vy': random.uniform(-1, 1) * particle_max_speed,
        'color': random.choice([(255, 0, 0), (0, 0, 255), (255, 255, 0)]),  # Red, Blue, or Cyan
        'size': random.randint(1, 3)
    }
    particles.append(particle)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    if frame < explosion_start:
        # Normal atom animation
        progress = frame / explosion_start

        # Calculate atom size and orbit radius (zoom effect)
        atom_size = int(min_atom_size + (max_atom_size - min_atom_size) * progress**2)
        orbit_radius = max(2, min_orbit_radius + (max_orbit_radius - min_orbit_radius) * (1 - progress**2))

        # Calculate atom center position (moving across the screen)
        atom_center_x = int(width * 0.8 - progress * width * 0.6)
        atom_center_y = int(height // 2)
        atom_center = (atom_center_x, atom_center_y)

        # Draw nucleus
        nucleus_angle = frame * 0.1
        nucleus_img = create_nucleus(atom_size, nucleus_angle)
        x_offset = atom_center[0] - atom_size // 2
        y_offset = atom_center[1] - atom_size // 2

        # Ensure the nucleus is within the frame
        x_start = max(0, x_offset)
        y_start = max(0, y_offset)
        x_end = min(width, x_offset + atom_size)
        y_end = min(height, y_offset + atom_size)

        img_x_start = x_start - x_offset
        img_y_start = y_start - y_offset
        img_x_end = img_x_start + (x_end - x_start)
        img_y_end = img_y_start + (y_end - y_start)

        img[y_start:y_end, x_start:x_end] = nucleus_img[img_y_start:img_y_end, img_x_start:img_x_end]

        # Calculate electron speed (increases as zoom progresses)
        electron_speed = base_electron_speed * (1 + progress * 5)

        # Calculate electron positions
        angle1 = frame * electron_speed
        angle2 = frame * electron_speed + math.pi
        e1_x = int(atom_center[0] + orbit_radius * math.cos(angle1))
        e1_y = int(atom_center[1] + orbit_radius * math.sin(angle1))
        e2_x = int(atom_center[0] + orbit_radius * math.cos(angle2))
        e2_y = int(atom_center[1] + orbit_radius * math.sin(angle2))

        # Draw electron traces
        for i in range(trace_length):
            trace_angle1 = (frame - i * 0.5) * electron_speed
            trace_angle2 = (frame - i * 0.5) * electron_speed + math.pi
            trace_radius = max(2, min_orbit_radius + (orbit_radius - min_orbit_radius) * ((frame - i * 0.5) / frame) if frame > 0 else min_orbit_radius)
            trace_x1 = int(atom_center[0] + trace_radius * math.cos(trace_angle1))
            trace_y1 = int(atom_center[1] + trace_radius * math.sin(trace_angle1))
            trace_x2 = int(atom_center[0] + trace_radius * math.cos(trace_angle2))
            trace_y2 = int(atom_center[1] + trace_radius * math.sin(trace_angle2))

            alpha = int(255 * (1 - i / trace_length))
            color = tuple(int(c * alpha / 255) for c in electron_color)
            cv2.circle(img, (trace_x1, trace_y1), electron_size, color, -1)
            cv2.circle(img, (trace_x2, trace_y2), electron_size, color, -1)

        # Draw electrons
        cv2.circle(img, (e1_x, e1_y), electron_size, electron_color, -1)
        cv2.circle(img, (e2_x, e2_y), electron_size, electron_color, -1)

    else:
        # Explosion animation
        explosion_progress = (frame - explosion_start) / (total_frames - explosion_start)

        for particle in particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']

            # Fade out particles
            alpha = int(255 * (1 - explosion_progress))
            color = tuple(int(c * alpha / 255) for c in particle['color'])

            cv2.circle(img, (int(particle['x']), int(particle['y'])), particle['size'], color, -1)

    # Add some glow
    img_glow = cv2.GaussianBlur(img, (5, 5), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: ../media/videos/atom.mp4")
