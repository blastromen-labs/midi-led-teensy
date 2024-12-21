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
out = cv2.VideoWriter(os.path.join(output_dir, 'helix.mp4'), fourcc, fps, (width, height))

# Create a binary file for LED output
binary_output = open(os.path.join(output_dir, 'helix.bin'), 'wb')

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

# Helix properties
helix_points = 100  # Increased number of points for smoother helix
radius = 100  # Initial radius of the helix
vertical_stretch = 1.5  # Vertical stretch factor
rotation_speed = 2  # Speed of rotation
zoom_speed = 0.8  # Increased zoom speed
line_thickness = 4  # Thickness of the helix lines
point_radius = 6  # Slightly smaller points for better look

# Colors
RED = (0, 0, 255)
BLUE = (255, 0, 0)

def draw_helix(img, frame, zoom_factor):
    center_x = width // 2
    center_y = height // 2

    # Calculate base rotation for this frame
    base_rotation = frame * rotation_speed * math.pi / 180

    # Create more points for smoother curves
    points_per_turn = 40
    num_turns = 6
    total_points = points_per_turn * num_turns

    # Lists to store all points from both helixes with their depth info
    all_points = []

    # Generate points for both helixes
    for i in range(total_points):
        phase = i * 2 * math.pi / points_per_turn + base_rotation
        y_offset = (i - total_points/2) * vertical_stretch * 8 * zoom_factor
        y = center_y + y_offset

        if 0 <= y < height:
            # Calculate 3D coordinates
            x_base = math.sin(phase) * radius * zoom_factor
            z_base = math.cos(phase) * radius * zoom_factor

            # Add points for both helixes with their color info
            all_points.append({
                'x': center_x + x_base,
                'y': y,
                'z': z_base,
                'color': RED,
                'phase': phase
            })
            all_points.append({
                'x': center_x - x_base,
                'y': y,
                'z': -z_base,
                'color': BLUE,
                'phase': phase
            })

    # Sort points by Z coordinate for proper depth rendering
    all_points.sort(key=lambda p: p['z'], reverse=True)

    # Group points by color and phase for continuous lines
    red_segments = {}
    blue_segments = {}

    for point in all_points:
        phase_key = int(point['phase'] * 10) / 10  # Round to help grouping
        if point['color'] == RED:
            if phase_key not in red_segments:
                red_segments[phase_key] = []
            red_segments[phase_key].append(point)
        else:
            if phase_key not in blue_segments:
                blue_segments[phase_key] = []
            blue_segments[phase_key].append(point)

    # Draw segments in order of depth
    for point in all_points:
        phase_key = int(point['phase'] * 10) / 10
        segments = red_segments if point['color'] == RED else blue_segments
        if phase_key in segments:
            segment = segments[phase_key]

            # Calculate depth-based brightness
            z_normalized = (point['z'] + radius) / (2 * radius)
            # Enhanced depth effect with more dramatic falloff
            brightness = 0.1 + 0.9 * (z_normalized ** 2)  # Quadratic falloff

            color = tuple(int(c * brightness) for c in point['color'])

            # Draw line segment
            points = np.array([(int(p['x']), int(p['y'])) for p in segment])
            if len(points) > 1:
                thickness = max(1, int((line_thickness + 3 * z_normalized) * zoom_factor))
                cv2.polylines(img, [points], False, color, thickness, lineType=cv2.LINE_AA)

            # Draw point
            point_size = int((point_radius + 3 * z_normalized) * zoom_factor)
            cv2.circle(img, (int(point['x']), int(point['y'])),
                      point_size, color, -1, lineType=cv2.LINE_AA)

            # Remove drawn segment to avoid redrawing
            segments.pop(phase_key, None)

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate zoom factor (starting very zoomed in, then zooming out)
    t = frame / total_frames
    zoom_factor = 3.0 - t * zoom_speed * 2.5  # Start more zoomed in, zoom out more

    # Draw the helix
    draw_helix(img, frame, zoom_factor)

    # Add stronger glow effect
    img_glow = cv2.GaussianBlur(img, (21, 21), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.7, 0)

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

print(f"Video generated: {os.path.join(output_dir, 'helix.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'helix.bin')}")