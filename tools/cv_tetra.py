import cv2
import numpy as np
import math
import os

# Video settings
width, height = 400, 960
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('tetra.mp4', fourcc, fps, (width, height))

# Create a binary file for 32x96 output
binary_output = open('tetra.bin', 'wb')

# Tetrahedron properties
base_tetra_size = min(width, height) * 0.6  # Increased from 0.3 to 0.6
tetra_colors = [
    (0, 0, 255),    # Red
    (0, 255, 0),    # Green
    (255, 0, 0),    # Blue
    (128, 128, 128) # Gray (for the fourth face)
]

# Define tetrahedron vertices
base_vertices = np.float32([
    [1, 1, 1],
    [-1, -1, 1],
    [-1, 1, -1],
    [1, -1, -1]
])

# Define tetrahedron faces
faces = [
    (0, 1, 2),
    (0, 1, 3),
    (0, 2, 3),
    (1, 2, 3)
]

def rotate_points(points, angle_y, angle_x):
    # Rotation matrix for y-axis rotation
    Ry = np.array([
        [math.cos(angle_y), 0, math.sin(angle_y)],
        [0, 1, 0],
        [-math.sin(angle_y), 0, math.cos(angle_y)]
    ])
    # Rotation matrix for x-axis rotation
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(angle_x), -math.sin(angle_x)],
        [0, math.sin(angle_x), math.cos(angle_x)]
    ])
    return np.dot(np.dot(points, Ry.T), Rx.T)

def draw_polygon(img, points, color, depth_buffer):
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)

    y_indices, x_indices = np.where(mask > 0)
    for y, x in zip(y_indices, x_indices):
        if 0 <= x < width and 0 <= y < height:
            z = depth_buffer[y, x]
            if z > 0:
                img[y, x] = color

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)
    depth_buffer = np.full((height, width), np.inf)

    # Calculate rotation angles
    angle_y = frame * 2 * math.pi / (fps * 5)  # Full horizontal rotation every 5 seconds
    angle_x = frame * 2 * math.pi / (fps * 7)  # Full vertical rotation every 7 seconds

    # Calculate zoom factor (oscillating between 0.5 and 1.5)
    zoom_factor = 1 + 0.5 * math.sin(frame * 2 * math.pi / (fps * 5))
    tetra_size = base_tetra_size * zoom_factor

    # Apply zoom to vertices
    vertices = base_vertices * tetra_size

    # Rotate the tetrahedron (horizontal and vertical spin)
    rotated_vertices = rotate_points(vertices, angle_y, angle_x)

    # Project 3D points to 2D space (orthographic projection)
    projected_points = (rotated_vertices[:, :2] * np.array([1, -1]) + [width/2, height/2]).astype(int)

    # Sort faces by depth (simple painter's algorithm)
    face_depth = [np.mean(rotated_vertices[list(face)][:, 2]) for face in faces]
    sorted_faces = sorted(enumerate(faces), key=lambda x: face_depth[x[0]], reverse=True)

    # Draw faces
    for i, face in sorted_faces:
        pts = projected_points[list(face)]
        draw_polygon(img, pts, tetra_colors[i], depth_buffer)

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
    adjusted = adjust_contrast_brightness(enhanced, contrast=0.9, brightness=-20)

    # Apply black threshold
    final = apply_black_threshold(adjusted, threshold=20)

    # Write to binary file
    binary_output.write(final.astype(np.uint8).tobytes())

# Release the VideoWriter and close the binary file
out.release()
binary_output.close()

print("Video generated: tetra.mp4")
print("Binary file generated: tetra.bin")
