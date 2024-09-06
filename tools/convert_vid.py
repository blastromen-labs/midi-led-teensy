import os
import subprocess

def find_ffmpeg():
    ffmpeg_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        "ffmpeg"  # This will work if ffmpeg is in PATH
    ]
    for path in ffmpeg_paths:
        if os.path.isfile(path) or path == "ffmpeg":
            return path
    raise FileNotFoundError("FFmpeg not found. Please install FFmpeg and add it to your PATH or specify its location in the script.")

def convert_and_upscale_video(input_file, output_file):
    ffmpeg_path = find_ffmpeg()

    # Use FFmpeg to posterize, increase contrast, resize to 32x16, and then upscale to 640x320
    ffmpeg_command = [
        ffmpeg_path,
        "-i", input_file,
        "-vf", "pp=ac/al,eq=contrast=2:brightness=0.1,scale=32:16:flags=neighbor,scale=640:320:flags=neighbor",
        "-c:v", "libx264",
        "-preset", "veryslow",
        "-crf", "18",
        "-c:a", "copy",
        output_file
    ]
    subprocess.run(ffmpeg_command, check=True)

def process_videos_in_directory(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.mp4', '.mov')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"converted_{filename}")
            print(f"Converting {filename}...")
            convert_and_upscale_video(input_path, output_path)
            print(f"Converted {filename} to {output_path}")

if __name__ == "__main__":
    input_directory = "../media/videos/temp"
    output_directory = "../media/videos/temp/out"
    process_videos_in_directory(input_directory, output_directory)
