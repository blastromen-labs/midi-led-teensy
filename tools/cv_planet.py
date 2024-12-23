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
out = cv2.VideoWriter(os.path.join(output_dir, 'planet.mp4'), fourcc, fps, (width, height))

# Create a binary file for LED output
binary_output = open(os.path.join(output_dir, 'planet.bin'), 'wb')

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

# Planet properties
initial_planet_radius = 400
planet_color = (0, 255, 255)  # Yellow in BGR
ring_color = (255, 128, 0)    # Blue in BGR
ring_tilt = 25
horizontal_faces = 12  # Reduced for larger triangles
vertical_faces = 8
ring_thickness = 6

def draw_planet_and_rings(img, center, radius, frame):
    # Calculate ring properties
    ring_inner_radius = int(radius * 1.4)
    ring_outer_radius = int(radius * 2.2)

    # Draw back half of ring (continuous)
    for r in range(ring_inner_radius, ring_outer_radius, 2):
        ring_progress = (r - ring_inner_radius) / (ring_outer_radius - ring_inner_radius)
        opacity = math.sin(ring_progress * math.pi) * 0.8

        cv2.ellipse(img, center, (r, int(r * 0.3)),
                   ring_tilt, 180, 360,
                   tuple(int(c * opacity * 0.3) for c in ring_color),
                   ring_thickness)

    # Draw polyhedron planet
    vertices = []
    faces = []
    face_depths = []

    # Generate vertices for sphere
    for i in range(vertical_faces + 1):
        v_angle = (i * math.pi) / vertical_faces
        y_radius = radius * math.sin(v_angle)
        y = center[1] + radius * math.cos(v_angle)

        for j in range(horizontal_faces):
            h_angle = (j * 2 * math.pi) / horizontal_faces
            x = center[0] + y_radius * math.cos(h_angle)
            z = y_radius * math.sin(h_angle)
            vertices.append((int(x), int(y), z))

    # Generate faces
    for i in range(vertical_faces):
        for j in range(horizontal_faces):
            v1 = i * horizontal_faces + j
            v2 = i * horizontal_faces + ((j + 1) % horizontal_faces)
            v3 = (i + 1) * horizontal_faces + ((j + 1) % horizontal_faces)
            v4 = (i + 1) * horizontal_faces + j

            face1 = [vertices[v1], vertices[v2], vertices[v3]]
            face2 = [vertices[v1], vertices[v3], vertices[v4]]

            # Calculate face normals for better shading
            def calculate_normal(face):
                v0, v1, v2 = face
                dx1, dy1, dz1 = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
                dx2, dy2, dz2 = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
                nx = dy1*dz2 - dz1*dy2
                ny = dz1*dx2 - dx1*dz2
                nz = dx1*dy2 - dy1*dx2
                return nz  # We mainly care about Z component for visibility

            depth1 = calculate_normal(face1)
            depth2 = calculate_normal(face2)

            faces.append((face1, depth1))
            faces.append((face2, depth2))

    # Sort faces by depth
    faces.sort(key=lambda x: x[1])

    # Draw faces
    for face, depth in faces:
        points = np.array([(int(v[0]), int(v[1])) for v in face], np.int32)

        # Enhanced depth-based shading
        depth_factor = (depth + radius) / (2 * radius)

        # Calculate edge factor based on position from center
        center_point = np.mean(points, axis=0)
        distance_from_center = np.sqrt(np.sum((center_point - np.array([center[0], center[1]]))**2))
        edge_factor = distance_from_center / radius

        # Combine factors for final brightness
        brightness = max(0.1, min(1.0, 1.0 - edge_factor * 0.8))
        brightness *= max(0.2, depth_factor)

        # Draw solid face with darker edges
        color = tuple(int(c * brightness) for c in planet_color)
        cv2.fillPoly(img, [points], color)

        # Draw thicker black edges
        cv2.polylines(img, [points], True, (0, 0, 0), 3)

        # Draw slightly thinner dark yellow edges
        edge_color = tuple(int(c * brightness * 0.3) for c in planet_color)
        cv2.polylines(img, [points], True, edge_color, 2)

    # Draw front half of ring
    for r in range(ring_inner_radius, ring_outer_radius, 2):
        ring_progress = (r - ring_inner_radius) / (ring_outer_radius - ring_inner_radius)
        opacity = math.sin(ring_progress * math.pi) * 0.8

        cv2.ellipse(img, center, (r, int(r * 0.3)),
                   ring_tilt, 0, 180,
                   tuple(int(c * opacity) for c in ring_color),
                   ring_thickness)

    # Add simple highlight (no gradient)
    highlight_size = int(radius * 0.2)
    highlight_points = np.array([
        [center[0] - highlight_size, center[1] - highlight_size],
        [center[0] - highlight_size//2, center[1] - highlight_size],
        [center[0] - highlight_size//2, center[1] - highlight_size//2]
    ], np.int32)
    cv2.fillPoly(img, [highlight_points], (0, 255, 255))  # Bright yellow highlight

# Animation loop
for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Faster zoom out with modified curve
    progress = frame / total_frames
    zoom_factor = 1 - (progress * 0.95) ** 0.5  # Even more aggressive zoom out

    # Calculate planet radius for this frame
    current_radius = int(initial_planet_radius * zoom_factor)

    # Center coordinates
    center = (width // 2, height // 2)

    # Draw planet and rings
    draw_planet_and_rings(img, center, current_radius, frame)

    # Enhanced glow effect
    glow = cv2.GaussianBlur(img, (25, 25), 0)
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

print(f"Video generated: {os.path.join(output_dir, 'planet.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'planet.bin')}")