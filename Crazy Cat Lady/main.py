import pygame
import sys
import os
import random
import math

pygame.init()

# Load and play background music
pygame.mixer.init()  # make sure the mixer is initialized
pygame.mixer.music.load("soundtrack.mp3")  # replace with your music file
pygame.mixer.music.set_volume(0.5)       # volume from 0.0 to 1.0
pygame.mixer.music.play(-1)              # -1 means loop forever


meow_sounds = [
   pygame.mixer.Sound("catmeow.mp3")
]

for sound in meow_sounds:
    sound.set_volume(0.6)

# --------------------
# Window
# --------------------
WIDTH, HEIGHT = 800, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Crazy Cat Lady")
clock = pygame.time.Clock()

# --------------------
# Colors
# --------------------
TEXT_COLOR = (50, 50, 50)
GROUND_COLOR = (200, 230, 180)  # lighter ground
HILL_COLOR = (120, 180, 120)    # darker hills
CLOUD_COLOR = (255, 255, 255, 200)
FLOWER_COLOR = (255, 150, 200)
BUSH_COLOR = (100, 150, 100)

# --------------------
# World settings
# --------------------
WORLD_WIDTH = 4000

# --------------------
# Player
# --------------------
player_rect = pygame.Rect(100, HEIGHT - 120, 40, 60)
player_vel_x = 0
player_vel_y = 0
speed = 3
jump_strength = -16
gravity = 0.8
on_ground = False

# --------------------
# Load player frames
# --------------------
player_frames = {"walk": [], "jump": [], "idle": []}
frame_folder = "player_frames"
TARGET_WIDTH = 40
TARGET_HEIGHT = 60

for filename in sorted(os.listdir(frame_folder)):
    if filename.endswith(".png"):
        img = pygame.image.load(os.path.join(frame_folder, filename)).convert_alpha()
        img = pygame.transform.scale(img, (TARGET_WIDTH, TARGET_HEIGHT))
        if filename.startswith("walk"):
            player_frames["walk"].append(img)
        elif filename.startswith("jump"):
            player_frames["jump"].append(img)
        elif filename.startswith("idle") or filename == "idle.png":
            player_frames["idle"].append(img)
# =============================
# Initialize frames safely
# =============================
frames = player_frames["idle"] if player_frames["idle"] else [pygame.Surface((TARGET_WIDTH, TARGET_HEIGHT), pygame.SRCALPHA)]
current_frame = 0
frame_timer = 0
frame_speed = 10

# --------------------
# Ground
# --------------------
ground_rect = pygame.Rect(0, HEIGHT - 60, WORLD_WIDTH, 60)

# --------------------
# Spawn blocking rect
# --------------------
blocking_rects = []

def can_place(rect, padding=6):
    test = rect.inflate(padding, padding)

    # Check static blocked areas
    for r in blocking_rects:
        if test.colliderect(r):
            return False

    # Check active (uncollected) cats
    for cat in cats:
        if not cat["collected"] and test.colliderect(cat["rect"]):
            return False

    return True


def register_rect(rect):
    blocking_rects.append(rect)


# --------------------
# Bushes
# --------------------
def draw_bush(screen, bush_rect, camera_x):
    base_x = bush_rect.x - camera_x
    base_y = bush_rect.y + bush_rect.height  # anchor to ground

    greens = [
        (95, 140, 95),
        (85, 130, 85),
        (75, 120, 75)
    ]

    circles = [
        (-5, -8, 10),
        (8, -14, 14),
        (22, -10, 12),
        (4, -20, 12),
        (16, -22, 10)
    ]

    for i, (dx, dy, r) in enumerate(circles):
        pygame.draw.circle(
            screen,
            greens[i % len(greens)],
            (int(base_x + dx), int(base_y + dy)),
            r
        )


# --------------------
# Platforms (varied, reachable, non-overlapping, fully separated)
# --------------------
platforms = []
x = 500
MIN_PLATFORM_WIDTH = 80
MAX_PLATFORM_WIDTH = 150
MIN_GAP = 100
MAX_GAP = 250
MAX_JUMP_HEIGHT = abs(jump_strength * 1.5 / gravity)
MIN_VERTICAL_GAP = 20  # pixels between any two platforms

last_y = HEIGHT - 100  # starting near the ground

while x < WORLD_WIDTH - 200:
    width = random.randint(MIN_PLATFORM_WIDTH, MAX_PLATFORM_WIDTH)
    height = HEIGHT - random.randint(120, 250)

    # Clamp height to be reachable from previous platform
    if last_y - height > MAX_JUMP_HEIGHT:
        height = last_y - int(MAX_JUMP_HEIGHT)

    base_platform = pygame.Rect(x, height, width, 10)
    platforms.append(base_platform)

    # Occasionally add a nearby higher platform
    if random.random() < 0.3:
        higher_width = random.randint(60, 120)
        offset_x = random.randint(-50, 50)
        offset_y = random.randint(20, int(MAX_JUMP_HEIGHT - 10))
        higher_x = max(0, min(x + offset_x, WORLD_WIDTH - higher_width))
        higher_y = max(50, height - offset_y)

        new_higher = pygame.Rect(higher_x, higher_y, higher_width, 10)

        # Only add if it does not overlap ANY existing platform (horizontal OR vertical)
        conflict = False
        for p in platforms:
            if new_higher.colliderect(p) or abs(new_higher.top - p.bottom) < MIN_VERTICAL_GAP or abs(new_higher.bottom - p.top) < MIN_VERTICAL_GAP:
                conflict = True
                break

        if not conflict:
            platforms.append(new_higher)

    last_y = height
    x += width + random.randint(MIN_GAP, MAX_GAP)

# --------------------
# Load cat sprites
# --------------------
cat_images = []
cat_folder = "cat_sprites"
target_height = 50  # desired height
cat_size = target_height
for i in range(1, 7):
    img = pygame.image.load(os.path.join(cat_folder, f"cat{i}.png")).convert_alpha()
    scale_factor = target_height / img.get_height()
    target_width = int(img.get_width() * scale_factor)
    img = pygame.transform.scale(img, (target_width, target_height))
    cat_images.append(img)

# --------------------
# Cats list
# --------------------
cats = []

def spawn_cats_on_surface(surface_rect, count=1):
    active_cats = [c for c in cats if not c["collected"]]
    for _ in range(count):
        if surface_rect.width >= cat_size:
            for attempt in range(10):
                x = surface_rect.x + random.randint(0, surface_rect.width - cat_size)
                cat_rect = pygame.Rect(x, 0, cat_size, cat_size)
                cat_rect.bottom = surface_rect.top if surface_rect != ground_rect else ground_rect.top

                # Only place if it does NOT collide with anything
                if can_place(cat_rect):
                    cats.append({
                        "rect": cat_rect,
                        "image": random.choice(cat_images),
                        "collected": False
                    })
                    register_rect(cat_rect)  # Block this spot for future spawns
                    break


# Spawn initial cats
spawn_cats_on_surface(ground_rect, count=3)
for plat in platforms:
    spawn_cats_on_surface(plat, count=1)

cat_count = 0

# --------------------
# Camera
# --------------------
camera_x = 0

# --------------------
# Font for counter
# --------------------
font = pygame.font.SysFont(None, 36)

# --------------------
# Basket icon
# --------------------
basket_img = pygame.image.load("basket.png").convert_alpha()

BASKET_HEIGHT = 32
scale = BASKET_HEIGHT / basket_img.get_height()
basket_img = pygame.transform.scale(
    basket_img,
    (int(basket_img.get_width() * scale), BASKET_HEIGHT)
)


# --------------------
# Parallax backgrounds
# --------------------
bg_sky = pygame.Surface((WORLD_WIDTH, HEIGHT))
bg_sky.fill((180, 220, 255))  # light blue sky

# --------------------
# Layered Hills with drifting fog and trees
# --------------------
hill_layers = [
    ((185, 215, 185), 190, 60, 90, 300, 0.15),  # far hills
    ((150, 195, 150), 160, 90, 140, 260, 0.3),  # mid hills
    ((115, 170, 115), 130, 140, 200, 220, 0.5)  # near hills
]



bg_hills = []


for index, (color, y_offset, min_h, max_h, spacing, parallax) in enumerate(hill_layers):
    surface = pygame.Surface((WORLD_WIDTH, HEIGHT), pygame.SRCALPHA)
    # Solid base to prevent sky gaps between hills
    pygame.draw.rect(
       surface,
       color,
       (0, HEIGHT - y_offset + min_h // 2, WORLD_WIDTH, HEIGHT)
)


    x = -spacing
    while x < WORLD_WIDTH + spacing:
        base_width = random.randint(260, 420)
        base_height = random.randint(min_h, max_h)
        base_y = HEIGHT - y_offset

        # Draw main hill
        pygame.draw.ellipse(surface, color, (x, base_y, base_width, base_height))

        # Add small wobble only for mid/near hills
        if index != 0:
            for _ in range(random.randint(1, 2)):
                wobble_w = base_width + random.randint(-60, 60)
                wobble_h = base_height + random.randint(-30, 30)
                wobble_x = x + random.randint(-40, 40)
                wobble_y = base_y + random.randint(-20, 20)
                pygame.draw.ellipse(surface, color, (wobble_x, wobble_y, wobble_w, wobble_h))

   

        x += spacing + random.randint(-60, 60)

    bg_hills.append({"surface": surface, "parallax": parallax})






# Clouds layer
clouds = []
for i in range(0, WORLD_WIDTH, 250):
    cx = i + random.randint(-20, 20)
    cy = 50 + random.randint(-20, 20)

    # Random cloud size
    cloud_w = random.randint(120, 200)
    cloud_h = random.randint(60, 100)

    cloud_surface = pygame.Surface((cloud_w, cloud_h), pygame.SRCALPHA)

    # --- Base cloud body (guarantees visibility) ---
    pygame.draw.ellipse(
        cloud_surface,
        CLOUD_COLOR,
        (int(cloud_w * 0.1), int(cloud_h * 0.3),
         int(cloud_w * 0.8), int(cloud_h * 0.6))
    )

    # --- Additional fluffy blobs ---
    blob_count = random.randint(3, 6)
    for _ in range(blob_count):
        w = random.randint(cloud_w // 4, cloud_w // 2)
        h = random.randint(cloud_h // 3, int(cloud_h * 0.8))

        max_x = max(0, cloud_w - w)
        max_y = max(0, cloud_h - h)

        x = random.randint(0, max_x)
        y = random.randint(int(cloud_h * 0.15), max_y)

        pygame.draw.ellipse(
            cloud_surface,
            CLOUD_COLOR,
            (x, y, w, h)
        )
    cloud_surface.set_alpha(180)

    clouds.append({
        "surface": cloud_surface,
        "x": cx,
        "y": cy,
        "speed": random.uniform(0.1, 0.3)
        
    })


# --------------------
# Foreground flowers & bushes
# --------------------
flowers = []
FLOWER_W, FLOWER_H = 20, 30

for i in range(0, WORLD_WIDTH, 140):
    for _ in range(10):
        x = i + random.randint(0, 60)
        y = HEIGHT - 60
        rect = pygame.Rect(x - FLOWER_W // 2, y - FLOWER_H, FLOWER_W, FLOWER_H)

        if can_place(rect):
            register_rect(rect)
            flowers.append({
                "x": x,
                "y": y,
                "angle": random.uniform(0, math.pi * 2),
                "color": random.choice([
                    (255, 160, 190),
                    (255, 220, 120),
                    (180, 200, 255),
                    (220, 180, 255)
                ]),
                "rect": rect
            })
            break


bushes = []
for i in range(0, WORLD_WIDTH, 300):
    for _ in range(10):
        rect = pygame.Rect(i + random.randint(0, 50), HEIGHT - 70, 30, 20)
        if can_place(rect):
            register_rect(rect)
            bushes.append(rect)
            break


# --------------------
# Cat spawning control
# --------------------
MAX_CATS_ON_SCREEN = 8
spawn_timer = 0
spawn_interval = 200  # spawn rate

# --------------------
# TITLE SCREEN (CLEAN VERSION)
# --------------------
def title_screen():
    pulse_timer = 0
    running_title = True

    # Fonts
    title_font = pygame.font.SysFont("Comic Sans MS", 80, bold=True)
    button_font = pygame.font.SysFont(None, 48)
    title_str = "Crazy Cat Lady"

    # Button setup
    button_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 50, 260, 60)
    button_color_default = (255, 180, 200)  # pastel pink
    button_color_hover = (200, 180, 255)    # pastel purple

    while running_title:
        clock.tick(60)
        pulse_timer += 1

        # --------------------
        # Events
        # --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    running_title = False
            if event.type == pygame.KEYDOWN:
                running_title = False

        # --------------------
        # Background
        # --------------------
        screen.fill((180, 220, 255))  # sky

        # Hills (same as game)
        for layer in bg_hills:
            screen.blit(layer["surface"], (-camera_x * layer["parallax"], 0))

        # Clouds (slower drift for calm effect)
        for cloud in clouds:
            cloud["x"] += cloud["speed"] * 0.2
            if cloud["x"] > WORLD_WIDTH:
                cloud["x"] = -150
            screen.blit(cloud["surface"], (cloud["x"] - camera_x * 0.3, cloud["y"]))

        # --------------------
        # Title text (cute + shadow)
        # --------------------
        # Shadow
        shadow_text = title_font.render(title_str, True, (200, 180, 200))
        screen.blit(shadow_text, (WIDTH//2 - shadow_text.get_width()//2 + 3,
                                  HEIGHT//3 + 3))

        # Main color
        title_text = title_font.render(title_str, True, (255, 180, 220))
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//3))

        # --------------------
        # Pulsing button with hover
        # --------------------
        mouse_pos = pygame.mouse.get_pos()
        hovering = button_rect.collidepoint(mouse_pos)

        color = button_color_hover if hovering else button_color_default
        pulse = 5 * math.sin(pulse_timer / 20)
        button_draw_rect = button_rect.inflate(pulse + (10 if hovering else 0),
                                              pulse + (10 if hovering else 0))

        pygame.draw.rect(screen, color, button_draw_rect, border_radius=15)

        button_text = button_font.render("Let's Get Crazy", True, (80, 50, 70))
        screen.blit(button_text, (button_draw_rect.centerx - button_text.get_width() // 2,
                                  button_draw_rect.centery - button_text.get_height() // 2))

        pygame.display.flip()

# Show the title screen first
title_screen()


# --------------------
# MAIN GAME LOOP
# --------------------
running = True
frames = player_frames["idle"]  # ensure frames is initialized
current_frame = 0
frame_timer = 0

while running:
    clock.tick(60)

    # --------------------
    # EVENTS
    # --------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --------------------
    # INPUT
    # --------------------
    keys = pygame.key.get_pressed()
    player_vel_x = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        player_vel_x = -speed
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        player_vel_x = speed
    if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        player_vel_y = jump_strength
        on_ground = False

    # --------------------
    # MOVEMENT
    # --------------------
    player_rect.x += player_vel_x
    player_vel_y += gravity
    player_rect.y += player_vel_y

    # --------------------
    # PLATFORM COLLISIONS
    # --------------------
    on_platform = False
    tolerance = 10

    if player_rect.colliderect(ground_rect):
        player_rect.bottom = ground_rect.top
        player_vel_y = 0
        on_platform = True
        on_ground = True

    for plat in platforms:
        if player_rect.colliderect(plat) and player_vel_y >= 0:
            if player_rect.bottom - player_vel_y <= plat.top + tolerance:
                player_rect.bottom = plat.top
                player_vel_y = 0
                on_platform = True
                on_ground = True

    if not on_platform:
        on_ground = False

    # --------------------
    # WORLD BOUNDS
    # --------------------
    player_rect.left = max(0, player_rect.left)
    player_rect.right = min(WORLD_WIDTH, player_rect.right)

    # --------------------
    # CAT COLLECTION
    # --------------------
    active_cats = [c for c in cats if not c["collected"]]
    for cat in active_cats:
        if player_rect.colliderect(cat["rect"]):
            cat["collected"] = True
            cat_count += 1
            random.choice(meow_sounds).play()

    # REMOVE this cat's rect from blocking_rects
        if cat["rect"] in blocking_rects:
            blocking_rects.remove(cat["rect"])

    # --------------------
    # DYNAMIC CAT SPAWNING
    # --------------------
    spawn_timer += 1
    if spawn_timer >= spawn_interval:
        spawn_timer = 0
        active_cats = [c for c in cats if not c["collected"]]
        if len(active_cats) < MAX_CATS_ON_SCREEN:
            cats_to_spawn = min(2, MAX_CATS_ON_SCREEN - len(active_cats))
            for _ in range(cats_to_spawn):
                plat = random.choice(platforms + [ground_rect])
                spawn_cats_on_surface(plat, count=1)

    # --------------------
    # CAMERA
    # --------------------
    camera_target = player_rect.centerx - WIDTH // 2
    camera_x += (camera_target - camera_x) * 0.1
    camera_x = max(0, min(camera_x, WORLD_WIDTH - WIDTH))

    # --------------------
    # PLAYER ANIMATION
    # --------------------
    previous_frames = frames  # remember the old frames

    if not on_ground and player_frames["jump"]:
        frames = player_frames["jump"]
    elif player_vel_x != 0 and player_frames["walk"]:
        frames = player_frames["walk"]
    else:
        frames = player_frames["idle"]

    # Reset current_frame if frames list changed
    if frames != previous_frames:
        current_frame = 0
        frame_timer = 0

    # Ensure there is at least one frame to avoid IndexError
    if len(frames) == 0:
        frames = [pygame.Surface((TARGET_WIDTH, TARGET_HEIGHT), pygame.SRCALPHA)]

    # Advance frame
    frame_timer += 1
    if frame_timer >= frame_speed:
        frame_timer = 0
        current_frame = (current_frame + 1) % len(frames)

    flip = player_vel_x < 0
    player_image = pygame.transform.flip(frames[current_frame], flip, False)



    # ==================================================
    # DRAW EVERYTHING
    # ==================================================
    screen.fill((180, 220, 255))  # sky

    # Hills
    for layer in bg_hills:
        screen.blit(layer["surface"], (-camera_x * layer["parallax"], 0))

    # Clouds
    for cloud in clouds:
        cloud["x"] += cloud["speed"]
        if cloud["x"] > WORLD_WIDTH:
            cloud["x"] = -150
        screen.blit(cloud["surface"], (cloud["x"] - camera_x * 0.3, cloud["y"]))

    # Ground
    pygame.draw.rect(screen, GROUND_COLOR,
                     pygame.Rect(ground_rect.x - camera_x, ground_rect.y,
                                 ground_rect.width, ground_rect.height),
                     border_radius=20)

    # Platforms
    for plat in platforms:
        pygame.draw.rect(screen, (200, 180, 240),
                         pygame.Rect(plat.x - camera_x, plat.y, plat.width, plat.height),
                         border_radius=5)

    # Flowers
    for flower in flowers:
        sway = math.sin(pygame.time.get_ticks() / 400 + flower["angle"]) * 4
        fx = flower["x"] + sway - camera_x
        fy = flower["y"]
        pygame.draw.line(screen, (90, 150, 90), (int(fx), int(fy)), (int(fx), int(fy - 18)), 2)
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            pygame.draw.circle(screen, flower["color"],
                               (int(fx + math.cos(rad) * 5), int(fy - 18 + math.sin(rad) * 5)), 4)
        pygame.draw.circle(screen, (255, 230, 120), (int(fx), fy - 18), 3)

    # Bushes
    for bush in bushes:
        draw_bush(screen, bush, camera_x)

    # Cats
    for cat in cats:
        if not cat["collected"]:
            screen.blit(cat["image"], (cat["rect"].x - camera_x, cat["rect"].y))

    # Player
    screen.blit(player_image, (player_rect.x - camera_x, player_rect.y))

    # HUD
    screen.blit(basket_img, (20, 10))
    count_text = font.render(str(cat_count), True, TEXT_COLOR)
    screen.blit(count_text, (20 + basket_img.get_width() + 8, 12))

    pygame.display.flip()

pygame.quit()
sys.exit()
