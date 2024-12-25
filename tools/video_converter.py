import cv2
import numpy as np
import os
import argparse

BRIGHTNESS_THRESHOLD = 0.05

def convert_video(input_file, output_name=None):
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
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Create binary output file
    binary_output = open(os.path.join(output_dir, f'{output_name}.bin'), 'wb')

    def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
        return cv2.addWeighted(image, contrast, image, 0, brightness)

    def apply_black_threshold(image, brightness_threshold=0.2):
        # Convert to HSV for better brightness handling
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # Normalize V channel to 0-1 range
        v_channel = hsv[:, :, 2].astype(float) / 255

        # Create mask where brightness is below threshold
        dark_mask = v_channel < brightness_threshold

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

        # Resize frame to match LED display aspect ratio first
        height, width = frame.shape[:2]
        target_height = 96
        target_width = 40

        # Calculate resize dimensions maintaining aspect ratio
        aspect_ratio = width / height
        target_aspect = target_width / target_height

        if aspect_ratio > target_aspect:
            # Video is wider than target, fit to height
            resize_height = target_height
            resize_width = int(resize_height * aspect_ratio)
        else:
            # Video is taller than target, fit to width
            resize_width = target_width
            resize_height = int(resize_width / aspect_ratio)

        # Resize frame
        resized = cv2.resize(frame, (resize_width, resize_height))

        # Crop to exact dimensions
        y_start = (resize_height - target_height) // 2
        x_start = (resize_width - target_width) // 2
        cropped = resized[y_start:y_start+target_height, x_start:x_start+target_width]

        # Ensure exact dimensions with final resize if needed
        final = cv2.resize(cropped, (target_width, target_height))

        # Convert to RGB for LED display
        frame_rgb = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)

        # Enhance image
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

        # Apply brightness-based black threshold
        final = apply_black_threshold(adjusted, brightness_threshold=BRIGHTNESS_THRESHOLD)

        # Write to binary file
        binary_output.write(final.astype(np.uint8).tobytes())

        # Progress indication
        frame_count += 1
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {progress:.1f}%")

    # Clean up
    cap.release()
    binary_output.close()

    print(f"\nConversion complete!")
    print(f"Binary file generated: {os.path.join(output_dir, f'{output_name}.bin')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert video to LED display binary format')
    parser.add_argument('input', help='Input video file path')
    parser.add_argument('--output', help='Output filename (without extension)', default=None)

    args = parser.parse_args()
    convert_video(args.input, args.output)