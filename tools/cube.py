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
out = cv2.VideoWriter(os.path.join(output_dir, 'cube.mp4'), fourcc, fps, (width, height))

# Create a binary file for LED output
binary_output = open(os.path.join(output_dir, 'cube.bin'), 'wb')

def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
    return cv2.addWeighted(image, contrast, image, 0, brightness)

def apply_black_threshold(image, threshold):
    return np.where(image < threshold, 0, image)

# Cube properties
cube_size = min(width, height) * 0.3
cube_color = (0, 0, 255)  # Red color
line_thickness = 8  # Increased thickness for better visibility

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

    # Project 3D points to 2D space (centered in frame)
    projected_points = (rotated_vertices[:, :2] + [width/2, height/2]).astype(int)

    # Draw the edges with glow effect
    for edge in edges:
        start = tuple(projected_points[edge[0]])
        end = tuple(projected_points[edge[1]])
        # Draw thick line for base
        cv2.line(img, start, end, cube_color, thickness=line_thickness)

    # Add glow effect
    img_glow = cv2.GaussianBlur(img, (15, 15), 0)
    img = cv2.addWeighted(img, 1, img_glow, 0.5, 0)

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

# Release the VideoWriter and close the binary file
out.release()
binary_output.close()

print(f"Video generated: {os.path.join(output_dir, 'cube.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'cube.bin')}")
