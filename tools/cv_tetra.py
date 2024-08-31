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
    (0, 0, 40),  # Dark red
    (0, 0, 80),  # Medium red
    (0, 0, 150),  # Bright red
    (0, 0, 255)   # Full red
]

# Define bright blue color for edges (BGR format)
edge_color = (255, 0, 0)  # Bright blue

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

# Define tetrahedron edges
edges = [
    (0, 1), (0, 2), (0, 3),
    (1, 2), (1, 3), (2, 3)
]

def rotate_points(points, angle_x, angle_y, angle_z):
    # Rotation matrices
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(angle_x), -math.sin(angle_x)],
        [0, math.sin(angle_x), math.cos(angle_x)]
    ])
    Ry = np.array([
        [math.cos(angle_y), 0, math.sin(angle_y)],
        [0, 1, 0],
        [-math.sin(angle_y), 0, math.cos(angle_y)]
    ])
    Rz = np.array([
        [math.cos(angle_z), -math.sin(angle_z), 0],
        [math.sin(angle_z), math.cos(angle_z), 0],
        [0, 0, 1]
    ])
    R = np.dot(Rz, np.dot(Ry, Rx))
    return np.dot(points, R.T)

def calculate_normal(v1, v2, v3):
    a = v2 - v1
    b = v3 - v1
    return np.cross(a, b)

def is_face_visible(normal, camera_position):
    return np.dot(normal, camera_position) > 0

def is_edge_visible(edge, visible_faces):
    return any(all(v in face for v in edge) for face in visible_faces)

def draw_polygon(img, points, color, depth_buffer):
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)

    y_indices, x_indices = np.where(mask > 0)
    for y, x in zip(y_indices, x_indices):
        if 0 <= x < width and 0 <= y < height:
            z = depth_buffer[y, x]
            if z > 0:
                img[y, x] = color

def draw_line(img, start, end, color, depth_buffer):
    x0, y0, z0 = start
    x1, y1, z1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    dz = abs(z1 - z0)

    if dx == 0 and dy == 0:
        # If start and end are the same point, just draw that point
        if 0 <= int(x0) < width and 0 <= int(y0) < height:
            if z0 < depth_buffer[int(y0), int(x0)]:
                img[int(y0), int(x0)] = color
                depth_buffer[int(y0), int(x0)] = z0
        return

    if dx > dy:
        steps = dx
    else:
        steps = dy

    if steps == 0:
        return  # Avoid division by zero

    x_increment = (x1 - x0) / steps
    y_increment = (y1 - y0) / steps
    z_increment = (z1 - z0) / steps

    x = x0
    y = y0
    z = z0

    for _ in range(int(steps) + 1):  # +1 to ensure the end point is included
        if 0 <= int(x) < width and 0 <= int(y) < height:
            if z < depth_buffer[int(y), int(x)]:
                img[int(y), int(x)] = color
                depth_buffer[int(y), int(x)] = z
        x += x_increment
        y += y_increment
        z += z_increment

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)
    depth_buffer = np.full((height, width), np.inf)

    # Calculate rotation angles
    angle_x = frame * 2 * math.pi / (fps * 8)
    angle_y = frame * 2 * math.pi / (fps * 6)
    angle_z = frame * 2 * math.pi / (fps * 10)

    # Calculate zoom factor (oscillating between 0.5 and 1.5)
    zoom_factor = 1 + 0.5 * math.sin(frame * 2 * math.pi / (fps * 5))
    tetra_size = base_tetra_size * zoom_factor

    # Apply zoom to vertices
    vertices = base_vertices * tetra_size

    # Rotate the tetrahedron
    rotated_vertices = rotate_points(vertices, angle_x, angle_y, angle_z)

    # Project 3D points to 2D space
    projected_points = (rotated_vertices[:, :2] + [width/2, height/2]).astype(int)

    # Draw faces
    for i, face in enumerate(faces):
        pts = projected_points[list(face)]
        z = np.mean(rotated_vertices[list(face)][:, 2])
        draw_polygon(img, pts, tetra_colors[i], depth_buffer)

    # Draw edges
    for edge in edges:
        start = tuple(projected_points[edge[0]]) + (rotated_vertices[edge[0], 2],)
        end = tuple(projected_points[edge[1]]) + (rotated_vertices[edge[1], 2],)
        draw_line(img, start, end, edge_color, depth_buffer)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: spinning_tetrahedron.mp4")
