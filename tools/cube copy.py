import cv2
import numpy as np
import math

# Video settings
scale_factor = 10
width, height = 32 * scale_factor, 16 * scale_factor
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('chq.mp4', fourcc, fps, (width, height))

# Cube properties
cube_size = min(width, height) * 0.4
cube_color = (255, 0, 0)  # Blue color at maximum brightness

# Define cube vertices
vertices = np.float32([
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
]) * cube_size

# Define cube edges
edges = [
    (0, 1), (1, 2), (2, 3), (3, 0),  # Back face
    (4, 5), (5, 6), (6, 7), (7, 4),  # Front face
    (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting edges
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

for frame in range(total_frames):
    # Create a black background
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Calculate rotation angles
    angle_x = frame * 2 * math.pi / (fps * 8)
    angle_y = frame * 2 * math.pi / (fps * 6)
    angle_z = frame * 2 * math.pi / (fps * 10)

    # Rotate the cube
    rotated_vertices = rotate_points(vertices, angle_x, angle_y, angle_z)

    # Project 3D points to 2D space
    projected_points = (rotated_vertices[:, :2] + [width/2, height/2]).astype(int)

    # Draw the edges
    for edge in edges:
        start = tuple(projected_points[edge[0]])
        end = tuple(projected_points[edge[1]])
        cv2.line(img, start, end, cube_color, thickness=scale_factor//2)

    # Write the frame
    out.write(img)

# Release the VideoWriter
out.release()

print("Video generated: rotating_3d_cube_hires_max.mp4")
