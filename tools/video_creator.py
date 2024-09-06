import pygame
from pygame.math import Vector3
from OpenGL.GL import *
from OpenGL.GLU import *
from moviepy.editor import ImageSequenceClip
import os
import math

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
CONTROL_WIDTH = 200
TOTAL_WIDTH = WIDTH + CONTROL_WIDTH

# Create a single window
screen = pygame.display.set_mode((TOTAL_WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("3D Retro Video Creator")

# Create a separate surface for controls
control_surface = pygame.Surface((CONTROL_WIDTH, HEIGHT))

# OpenGL initialization
glViewport(0, 0, WIDTH, HEIGHT)
glMatrixMode(GL_PROJECTION)
gluPerspective(45, WIDTH / HEIGHT, 0.1, 50.0)
glMatrixMode(GL_MODELVIEW)
glEnable(GL_DEPTH_TEST)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)

color_options = [RED, GREEN, BLUE, CYAN, MAGENTA, YELLOW, WHITE]
color_names = ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow", "White"]

class Object3D:
    def __init__(self, pos, color):
        self.pos = Vector3(pos)
        self.color = color
        self.rotation = Vector3(0, 0, 0)
        self.scale = 1.0

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos.x, self.pos.y, self.pos.z)
        glRotatef(self.rotation.x, 1, 0, 0)
        glRotatef(self.rotation.y, 0, 1, 0)
        glRotatef(self.rotation.z, 0, 0, 1)
        glScalef(self.scale, self.scale, self.scale)
        glColor3f(*[c/255 for c in self.color])
        self.draw_shape()
        glPopMatrix()

    def draw_shape(self):
        pass

class Cube(Object3D):
    def draw_shape(self):
        glBegin(GL_LINES)
        for edge in [(0,1),(0,3),(0,4),(2,1),(2,3),(2,7),(6,3),(6,4),(6,7),(5,1),(5,4),(5,7)]:
            for vertex in edge:
                glVertex3fv([(v-0.5)*self.scale for v in [(vertex//4)%2,(vertex//2)%2,vertex%2]])
        glEnd()

class Sphere(Object3D):
    def draw_shape(self):
        lats, longs = 16, 16
        for i in range(lats + 1):
            lat0 = math.pi * (-0.5 + float(i - 1) / lats)
            z0 = math.sin(lat0)
            zr0 = math.cos(lat0)
            lat1 = math.pi * (-0.5 + float(i) / lats)
            z1 = math.sin(lat1)
            zr1 = math.cos(lat1)
            glBegin(GL_LINE_STRIP)
            for j in range(longs + 1):
                lng = 2 * math.pi * float(j - 1) / longs
                x = math.cos(lng)
                y = math.sin(lng)
                glVertex3f(x * zr0 * 0.5, y * zr0 * 0.5, z0 * 0.5)
                glVertex3f(x * zr1 * 0.5, y * zr1 * 0.5, z1 * 0.5)
            glEnd()

class Tetrahedron(Object3D):
    def draw_shape(self):
        vertices = [(0, 0.5, 0), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0, -0.5, -0.5)]
        glBegin(GL_LINES)
        for edge in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()

buttons = [
    {"text": "Cube", "class": Cube},
    {"text": "Sphere", "class": Sphere},
    {"text": "Tetra", "class": Tetrahedron},
]

def ray_cast(x, y):
    viewport = glGetIntegerv(GL_VIEWPORT)
    modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    y = viewport[3] - y
    z = glReadPixels(x, int(y), 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)
    return Vector3(gluUnProject(x, y, z[0][0], modelview, projection, viewport))

def draw_controls():
    control_surface.fill((200, 200, 200))
    font = pygame.font.Font(None, 24)
    for i, button in enumerate(buttons):
        pygame.draw.rect(control_surface, (150, 150, 150), (10, i * 50 + 10, CONTROL_WIDTH - 20, 40))
        text = font.render(button["text"], True, BLACK)
        control_surface.blit(text, (20, i * 50 + 20))
    for i, color in enumerate(color_options):
        y = len(buttons) * 50 + i * 30 + 10
        pygame.draw.rect(control_surface, color, (10, y, 30, 20))
        text = font.render(color_names[i], True, BLACK)
        control_surface.blit(text, (50, y))

objects = []
clock = pygame.time.Clock()
selected_object = None
frames = []
camera_distance = 5

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if x > WIDTH:
                x -= WIDTH
                button_index = y // 50
                if button_index < len(buttons):
                    new_object = buttons[button_index]["class"]((0, 0, 0), RED)
                    objects.append(new_object)
                    selected_object = new_object
                elif len(buttons) * 50 <= y < len(buttons) * 50 + len(color_options) * 30:
                    if selected_object:
                        color_index = (y - len(buttons) * 50) // 30
                        selected_object.color = color_options[color_index]
            else:
                clicked_pos = ray_cast(x, y)
                selected_object = min(objects, key=lambda obj: (obj.pos - clicked_pos).length_squared(), default=None)
        elif event.type == pygame.MOUSEMOTION and selected_object and event.pos[0] <= WIDTH:
            dx, dy = event.rel
            if event.buttons[0]:
                selected_object.rotation.y += dx
                selected_object.rotation.x += dy
            elif event.buttons[2]:
                selected_object.pos.x += dx * 0.01
                selected_object.pos.y -= dy * 0.01
        elif event.type == pygame.MOUSEWHEEL and selected_object and event.pos[0] <= WIDTH:
            selected_object.scale = max(0.1, min(selected_object.scale + event.y * 0.1, 3.0))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                pygame.image.save(screen, "temp_frame.png")
                frames.append("temp_frame.png")
            elif event.key == pygame.K_DELETE:
                if selected_object in objects:
                    objects.remove(selected_object)
                    selected_object = None

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(0, 0, camera_distance, 0, 0, 0, 0, 1, 0)

    for obj in objects:
        if obj == selected_object:
            glColor3f(1, 1, 1)
        obj.draw()

    # Render the 3D scene to a surface
    data = glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGB, GL_UNSIGNED_BYTE)
    image = pygame.image.fromstring(data, (WIDTH, HEIGHT), "RGB", True)

    # Draw controls
    draw_controls()

    # Blit both surfaces to the screen
    screen.blit(image, (0, 0))
    screen.blit(control_surface, (WIDTH, 0))

    pygame.display.flip()
    clock.tick(60)

if frames:
    clip = ImageSequenceClip(frames, fps=30)
    clip.write_videofile("output.mp4")
    for frame in frames:
        os.remove(frame)

pygame.quit()
