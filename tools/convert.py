import cv2
import numpy as np
import os

def convert_video_to_binary(input_file, output_file, contrast_factor=0.9, brightness_offset=-20, black_threshold=20):
    def adjust_contrast_brightness(image, contrast=1.0, brightness=0):
        return cv2.addWeighted(image, contrast, image, 0, brightness)

    def apply_black_threshold(image, threshold):
        return np.where(image < threshold, 0, image)

    cap = cv2.VideoCapture(input_file)
    with open(output_file, 'wb') as f:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (32, 16))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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
            adjusted = adjust_contrast_brightness(enhanced, contrast_factor, brightness_offset)

            # Apply black threshold
            final = apply_black_threshold(adjusted, black_threshold)

            f.write(final.astype(np.uint8).tobytes())
    cap.release()

video_folder = '../media/videos/'
output_folder = '../media/sd_card_files/vid'
os.makedirs(output_folder, exist_ok=True)

video_files = [
    'space.mp4', 'cgi.mp4', 'car.mp4'
    # 'chq.mp4', 'a.mp4', 'rr.mp4', 'hii.mp4', 'hand.mp4',
    # 'tetra.mp4', 'packman.mp4', 'ball.mp4', 'cube_explode.mp4', 'blastrov.mp4', 'void.mp4'
]

for video_file in video_files:
    print(video_file)
    input_path = os.path.join(video_folder, video_file)
    output_path = os.path.join(output_folder, video_file.replace('.mp4', '.bin'))
    convert_video_to_binary(input_path, output_path)
    print(f"Converted {video_file} to {output_path}")
