from ursina import *
import cv2
import numpy as np
import math
import os

# Video settings
width, height = 400, 960
fps = 30
duration = 10  # seconds
total_frames = fps * duration

# Ensure output directory exists
output_dir = "../media"
os.makedirs(output_dir, exist_ok=True)

# Create video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(os.path.join(output_dir, 'human.mp4'), fourcc, fps, (width, height))
binary_output = open(os.path.join(output_dir, 'human.bin'), 'wb')

app = Ursina()
window.color = color._16  # Dark background like in Rubik's example
window.size = (width, height)
window.borderless = False
window.position = (0,0)

class HumanFigure(Entity):
    def __init__(self):
        super().__init__()
        head_size = 0.3

        # Create 3D torso using a diamond/pyramid shape
        self.body = Entity(
            parent=self,
            model='cube',
            scale=(head_size * 2, head_size * 3, head_size),  # Width, Height, Depth
            color=color.rgba(0, 1, 1, 1),
        )

        # Add depth to torso with additional shapes
        self.chest = Entity(
            parent=self.body,
            model='cube',
            scale=(head_size * 2, head_size * 1.5, head_size * 1.2),
            y=head_size * 0.5,
            color=color.rgba(0, 1, 1, 1),
        )

        # Spherical head
        self.head = Entity(
            parent=self.body,
            model='sphere',
            scale=head_size,
            y=head_size * 2,
            color=color.rgba(0, 1, 1, 1),
        )

        # Segmented arms with better proportions
        arm_segment = head_size * 1.2  # Longer segments
        arm_thickness = head_size * 0.25
        shoulder_width = head_size * 2

        # Left arm segments
        self.left_upper_arm = Entity(
            parent=self.body,
            model='cube',
            scale=(arm_segment * 1.2, arm_thickness, arm_thickness),
            x=-shoulder_width,
            y=head_size * 1,
            rotation_z=-15,  # Slight angle
            color=color.rgba(0, 1, 1, 1),
        )

        self.left_forearm = Entity(
            parent=self.left_upper_arm,
            model='cube',
            scale=(arm_segment, arm_thickness, arm_thickness),
            x=-arm_segment,
            rotation_z=-10,  # Additional angle
            color=color.rgba(0, 1, 1, 1),
        )

        self.left_hand = Entity(
            parent=self.left_forearm,
            model='cube',
            scale=(arm_segment * 0.4, arm_thickness * 1.2, arm_thickness * 1.2),
            x=-arm_segment,
            color=color.rgba(0, 1, 1, 1),
        )

        # Right arm segments (mirrored)
        self.right_upper_arm = Entity(
            parent=self.body,
            model='cube',
            scale=(arm_segment * 1.2, arm_thickness, arm_thickness),
            x=shoulder_width,
            y=head_size * 1,
            rotation_z=15,
            color=color.rgba(0, 1, 1, 1),
        )

        self.right_forearm = Entity(
            parent=self.right_upper_arm,
            model='cube',
            scale=(arm_segment, arm_thickness, arm_thickness),
            x=arm_segment,
            rotation_z=10,
            color=color.rgba(0, 1, 1, 1),
        )

        self.right_hand = Entity(
            parent=self.right_forearm,
            model='cube',
            scale=(arm_segment * 0.4, arm_thickness * 1.2, arm_thickness * 1.2),
            x=arm_segment,
            color=color.rgba(0, 1, 1, 1),
        )

        # Segmented legs with better proportions
        leg_segment = head_size * 1.8  # Much longer segments
        leg_thickness = head_size * 0.35
        hip_width = head_size * 0.9

        # Left leg segments
        self.left_thigh = Entity(
            parent=self.body,
            model='cube',
            scale=(leg_thickness, leg_segment * 1.2, leg_thickness),
            x=-hip_width,
            y=-head_size * 1.4,
            rotation_z=5,  # Slight angle
            color=color.rgba(0, 1, 1, 1),
        )

        self.left_shin = Entity(
            parent=self.left_thigh,
            model='cube',
            scale=(leg_thickness, leg_segment, leg_thickness),
            y=-leg_segment,
            rotation_z=-5,
            color=color.rgba(0, 1, 1, 1),
        )

        self.left_foot = Entity(
            parent=self.left_shin,
            model='cube',
            scale=(leg_thickness * 2, leg_thickness, leg_segment * 0.6),
            y=-leg_segment * 0.5,
            z=leg_thickness * 0.3,  # Add some depth
            color=color.rgba(0, 1, 1, 1),
        )

        # Right leg segments (mirrored)
        self.right_thigh = Entity(
            parent=self.body,
            model='cube',
            scale=(leg_thickness, leg_segment * 1.2, leg_thickness),
            x=hip_width,
            y=-head_size * 1.4,
            rotation_z=-5,
            color=color.rgba(0, 1, 1, 1),
        )

        self.right_shin = Entity(
            parent=self.right_thigh,
            model='cube',
            scale=(leg_thickness, leg_segment, leg_thickness),
            y=-leg_segment,
            rotation_z=5,
            color=color.rgba(0, 1, 1, 1),
        )

        self.right_foot = Entity(
            parent=self.right_shin,
            model='cube',
            scale=(leg_thickness * 2, leg_thickness, leg_segment * 0.6),
            y=-leg_segment * 0.5,
            z=leg_thickness * 0.3,
            color=color.rgba(0, 1, 1, 1),
        )

        # Initial position and scale
        self.y = 0
        self.scale = 14  # Increased overall scale
        self.rotation_x = 180

        # Animation properties
        self.rotation_speed = 60
        self.current_frame = 0

    def update(self):
        # Rotate the pivot instead of the figure
        pivot.rotation_y += time.dt * self.rotation_speed

        if self.current_frame < total_frames:
            try:
                screenshot = base.win.getScreenshot()
                if screenshot:
                    # Convert Panda3D image to numpy array correctly
                    img = np.frombuffer(screenshot.getRamImage(), np.uint8)
                    img = img.reshape((screenshot.getYSize(), screenshot.getXSize(), 4))

                    # Extract RGB channels (skip alpha)
                    b = img[:, :, 2]
                    g = img[:, :, 1]
                    r = img[:, :, 0]

                    # Calculate brightness/intensity of the original image
                    brightness = (r.astype(float) + g.astype(float) + b.astype(float)) / 3

                    # Create BGR image
                    img = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)

                    # Find non-black pixels
                    mask = brightness > 20

                    # Apply cyan color with preserved shading
                    # Scale both blue and green channels based on original brightness
                    img[:, :, 0][mask] = np.clip(brightness[mask] * 2, 0, 255).astype(np.uint8)  # Blue
                    img[:, :, 1][mask] = np.clip(brightness[mask] * 2, 0, 255).astype(np.uint8)  # Green
                    img[:, :, 2][mask] = 0  # Red channel stays 0 for cyan

                    # Resize to our target dimensions
                    img = cv2.resize(img, (width, height))

                    # Process frame for LED display
                    small_frame = cv2.resize(img, (40, 96))
                    # For LED display, convert BGR to RGB
                    frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    # Write frames
                    out.write(img)  # Write BGR for MP4
                    binary_output.write(frame_rgb.tobytes())  # Write RGB for LED

                    self.current_frame += 1
                    print(f"Frame {self.current_frame}/{total_frames}")
            except Exception as e:
                print(f"Error capturing frame: {e}")
                application.quit()
        else:
            application.quit()

# Create scene first
human = HumanFigure()

# Camera setup with better viewing angle
camera = EditorCamera()
camera.position = (0, 0, -6)  # Move camera back and level with figure
camera.rotation_x = 0  # Level camera angle

# Create a pivot point for the figure
pivot = Entity()
human.parent = pivot  # Now human exists when we parent it
human.y = 2  # Raise the figure to be centered in view

# Enhanced lighting for better visibility
main_light = DirectionalLight(parent=camera, y=2, z=-3, shadows=True)
fill_light = DirectionalLight(y=1, z=3, color=color.rgba(0.5, 0.5, 0.5, 1))
AmbientLight(color=color.rgba(0.7, 0.7, 0.7, 1))

# Run the app
app.run()

# Cleanup
out.release()
binary_output.close()
print(f"Video generated: {os.path.join(output_dir, 'human.mp4')}")
print(f"Binary file generated: {os.path.join(output_dir, 'human.bin')}")