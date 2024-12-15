import os
from PIL import Image

def convert_png_to_bin(input_file, output_file):
    with Image.open(input_file) as img:
        # Resize image to 40x96 pixels (matches the LED panel layout)
        img = img.resize((40, 96), Image.LANCZOS)

        # Ensure the image is in RGB mode
        img = img.convert('RGB')

        # Get raw RGB data
        raw_data = img.tobytes()

        # Write raw data to binary file
        with open(output_file, 'wb') as f:
            f.write(raw_data)

def process_directory(input_dir, output_dir):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process all PNG files in the input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.png'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.bin')

            print(f"Converting {filename}...")
            convert_png_to_bin(input_path, output_path)
            print(f"Created {os.path.basename(output_path)}")

if __name__ == "__main__":
    # Set your input and output directories here
    input_directory = '../media'
    output_directory = '../media'

    print("Starting PNG to binary conversion...")
    process_directory(input_directory, output_directory)
    print("Conversion complete!")
