import cv2
import numpy as np
import os

def convert_video_to_binary(input_file, output_file):
    cap = cv2.VideoCapture(input_file)
    with open(output_file, 'wb') as f:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (32, 16))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            f.write(frame_rgb.tobytes())
    cap.release()

video_folder = '../videos/'
output_folder = 'sd_card_files/'
os.makedirs(output_folder, exist_ok=True)

video_files = [
    'tunnel.mp4'
    # 'chq.mp4', 'a.mp4', 'rr.mp4', 'hii.mp4', 'hand.mp4',
    # 'tetra.mp4', 'packman.mp4', 'ball.mp4', 'cube_explode.mp4', 'blastrov.mp4', 'void.mp4'
]

for video_file in video_files:
    print(video_file)
    input_path = os.path.join(video_folder, video_file)
    output_path = os.path.join(output_folder, video_file.replace('.mp4', '.bin'))
    convert_video_to_binary(input_path, output_path)
    print(f"Converted {video_file} to {output_path}")
