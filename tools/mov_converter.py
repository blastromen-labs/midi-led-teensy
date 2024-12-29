import cv2
import numpy as np
import os
import argparse

BRIGHTNESS_THRESHOLD = 0.05  # 5% brightness threshold
TARGET_FPS = 30  # Target frame rate for LED display

def convert_mov(input_file, output_name=None):
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return

    # Create output directory if it doesn't exist
    output_dir = "../media"
    os.makedirs(output_dir, exist_ok=True)

    # If no output name specified, use input filename without extension
    if output_name is None:
        output_name = os.path.splitext(os.path.basename(input_file))[0]

    # Open the input video
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{input_file}'")
        return

    # Get video properties
    source_fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate frame skip to maintain proper speed
    frame_skip = max(1, round(source_fps / TARGET_FPS))

    # Create binary output file
    binary_output = open(os.path.join(output_dir, f'{output_name}.bin'), 'wb')

    def apply_black_threshold(image):
        # Convert to HSV for better brightness handling
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # Normalize V channel to 0-1 range
        v_channel = hsv[:, :, 2].astype(float) / 255

        # Create mask where brightness is below threshold
        dark_mask = v_channel < BRIGHTNESS_THRESHOLD

        # Create output array
        output = image.copy()
        # Set all channels to 0 where mask is True
        output[dark_mask] = 0

        return output

    # Process each frame
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Skip frames to maintain proper speed
        if frame_count % frame_skip != 0:
            frame_count += 1
            continue

        # Convert to RGB for LED display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Apply black threshold
        frame_thresholded = apply_black_threshold(frame_rgb)

        # Resize directly to LED display dimensions (40x96)
        final = cv2.resize(frame_thresholded, (40, 96))

        # Enhance contrast
        lab = cv2.cvtColor(final, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2,2))
        cl = clahe.apply(l)

        # Merge channels
        limg = cv2.merge((cl,a,b))

        # Convert back to RGB
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)

        # Write to binary file
        binary_output.write(enhanced.astype(np.uint8).tobytes())

        # Progress indication
        frame_count += 1
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {progress:.1f}%")
            print(f"Source FPS: {source_fps}, Frame skip: {frame_skip}")

    # Clean up
    cap.release()
    binary_output.close()

    print(f"\nConversion complete!")
    print(f"Binary file generated: {os.path.join(output_dir, f'{output_name}.bin')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert MOV video to LED display binary format')
    parser.add_argument('input', help='Input MOV file path')
    parser.add_argument('--output', help='Output filename (without extension)', default=None)

    args = parser.parse_args()
    convert_mov(args.input, args.output)