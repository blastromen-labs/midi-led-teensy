import cv2
import numpy as np
import math

# Video settings
width, height = 320, 160
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('spinning_tetrahedron.mp4', fourcc, fps, (width, height))

# Tetrahedron properties
base_tetra_size = min(width, height) * 0.3
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

def rotate_points(points, angle_y):
    # Rotation matrix for y-axis rotation
    Ry = np.array([
        [math.cos(angle_y), 0, math.sin(angle_y)],
        [0, 1, 0],
        [-math.sin(angle_y), 0, math.cos(angle_y)]
    ])
    return np.dot(points, Ry.T)

def draw_polygon(img, points, color, depth_buffer):
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)

    y_indices, x_indices = np.where(mask > 0)
    for y, x in zip(y_indices, x_indices):
        if 0 <= x < width and 0 <= y < height:
            z = depth_buffer[y, x]
            if z > 0:
                img[y, x] = color

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)
    depth_buffer = np.full((height, width), np.inf)

    # Calculate rotation angle (horizontal spin only)
    angle_y = frame * 2 * math.pi / (fps * 5)  # Full rotation every 5 seconds

    # Calculate zoom factor (oscillating between 0.5 and 1.5)
    zoom_factor = 1 + 0.5 * math.sin(frame * 2 * math.pi / (fps * 5))
    tetra_size = base_tetra_size * zoom_factor

    # Apply zoom to vertices
    vertices = base_vertices * tetra_size

    # Rotate the tetrahedron (horizontal spin only)
    rotated_vertices = rotate_points(vertices, angle_y)

    # Project 3D points to 2D space (orthographic projection)
    projected_points = (rotated_vertices[:, :2] * np.array([1, -1]) + [width/2, height/2]).astype(int)

    # Sort faces by depth (simple painter's algorithm)
    face_depth = [np.mean(rotated_vertices[list(face)][:, 2]) for face in faces]
    sorted_faces = sorted(enumerate(faces), key=lambda x: face_depth[x[0]], reverse=True)

    # Draw faces
    for i, face in sorted_faces:
        pts = projected_points[list(face)]
        draw_polygon(img, pts, tetra_colors[i], depth_buffer)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: spinning_tetrahedron.mp4")
