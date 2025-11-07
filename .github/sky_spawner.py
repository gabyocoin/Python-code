# FULL ARCADE SHOOTER: SUB WEAPONS + 4 BOSSES + BOMB + DINO HELPERS + SMOOTH LERP
# Integrated dino-chain + custom dino sprite + updated power-up system
import os, sys, time, random, pygame, math, traceback
from pygame import Rect
from math import hypot, sin, cos, radians

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 960, 540
FPS = 60
PLAYER_SPEED = 5.0
BULLET_SPEED = 13.0
ENEMY_MIN_SPEED, ENEMY_MAX_SPEED = 3.0, 5.5
ENEMY_BULLET_SPEED = 16.0
BOSS_SPAWN_SCORE = 5000
BOSS2_SPAWN_SCORE = 7500
BOSS3_SPAWN_SCORE = 15000
BOSS4_SPAWN_SCORE = 30000
MAX_LEVEL = 40
TRANSFORM_LEVEL = 15   # adjusted: transform now occurs at level 15
ROOT = os.path.dirname(os.path.abspath(__file__))
def ap(fn): return os.path.join(ROOT, fn)

# ---------------- SPAWN & RATE SCALING CONFIG ----------------
# Make these values to tune how spawn rate and firing rate scale with player level.
ENEMY_SPAWN_BASE_INTERVAL = 0.9        # base seconds between spawns at level 1
ENEMY_SPAWN_MIN_INTERVAL = 0.25       # minimum seconds between spawns (upper cap on spawn rate)
ENEMY_RATE_SCALE_PER_LEVEL = 0.02     # how much the multiplier reduces per level (per level step)
ENEMY_FIRE_MIN_MULT = 0.35            # minimum multiplier for enemy fire delay (can't be faster than this factor)
# ----------------------------------------------------------------

# ---------------- TRANSFORM / FLY / BULLET SHEET CONFIG ----------------
TRANSFORM_FLY_AMPLITUDE = 6.0     # pixels of vertical bobbing (visual only)
TRANSFORM_FLY_SPEED = 4.0         # bobbing speed (radians/sec)
TRANSFORM_MOVE_BOOST = 1.08       # small movement boost when transformed (1.0 = no change)
TRANSFORM_THRUST_PART_INTERVAL = 0.06  # seconds between emitted thrust particle bursts

# Transform animation frames + timing
TRANSFORM_ANIM_INTERVAL = 0.09    # seconds per transform-frame
transform_frames = []
transform_anim_index = 0
transform_anim_timer = 0.0

# Transform runtime visual state
transform_draw_offset = 0.0
transform_fly_phase = 0.0
transform_thrust_timer = 0.0

# Transform "bullet sheet" (spread) settings
TRANSFORM_BULLET_SHEET_COUNT = 5  # reduced bullets (less OP)
TRANSFORM_BULLET_SPREAD_DEG = 40  # narrower spread
TRANSFORM_BULLET_SPEED_MULT = 0.95 # slightly slower bullets
TRANSFORM_BULLET_DAMAGE_MULT = 0.8  # lower damage multiplier
TRANSFORM_SHEET_COOLDOWN = 0.6
transform_sheet_cooldown = 0.0

transform_bullet_imgs = []
# --------------------------------------------------------------------

# HIGH SCORE
HIGH_SCORE_FILE = "high_score.txt"
high_score = 0
if os.path.exists(HIGH_SCORE_FILE):
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            high_score = int(f.read().strip())
    except:
        high_score = 0

# BOMB SYSTEM
bomb_cooldown = 0.0
BOMB_COOLDOWN_TIME = 20.0
BOMB_INVUL_TIME = 5.0
player_invulnerable = False
invul_timer = 0.0
bomb_flash = 0.0

# SUB WEAPON SYSTEM
sub_weapon = "missile"
sub_weapons = ["missile", "laser", "lightning"]
sub_cycle_index = 0
sub_cooldown = 0.0
SUB_COOLDOWN_TIME = 2.0

# Custom sprite paths
sub_sprite_paths = {
    "missile": "assets/sub_missile.png",
    "laser": "assets/sub_laser.png",
    "lightning": "assets/sub_lightning.png"
}

# ---------------- DINO HELPER SYSTEM ----------------
MAX_HELPERS = 3
DINO_SPRITE_PATH = "assets/dino_helper.png"
CUSTOM_DINO_PATH = "assets/custom_dino.png"  # optional custom sprite
helpers = []
helper_count = 0
helper_spawn_timer = 0.0

# ---------------- SOUND INIT ----------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SKY RUINS — 4 BOSSES + DINO HELPERS + SMOOTH LERP")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20)
bigfont = pygame.font.SysFont("arial", 48, bold=True)

# ---------------- SOUND LOADERS ----------------
def load_sound_safe(name):
    path = ap(f"sounds/{name}")
    if os.path.exists(path):
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(0.5)
            return snd
        except Exception as e:
            print(f"Sound load failed ({name}): {e}")
    if name == "shoot.wav": return create_beep(800, 0.05)
    elif name == "hit.wav": return create_beep(400, 0.03)
    elif name == "explode.wav": return create_explosion()
    elif name == "powerup.wav": return create_sweep(600, 1200, 0.15)
    elif name == "boss.wav": return create_beep(150, 0.4)
    elif name == "victory.wav": return create_jingle()
    elif name == "levelup.wav": return create_rising(400, 1200, 0.4)
    elif name == "transform.wav": return create_powerup()
    elif name == "bomb.wav": return create_bomb_sound()
    return None

def create_beep(freq, duration):
    sample_rate = 44100
    frames = int(duration * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        value = int(32767 * 0.5 * math.sin(2 * math.pi * freq * t))
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

def create_sweep(f1, f2, duration):
    sample_rate = 44100
    frames = int(duration * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        freq = f1 + (f2 - f1) * (t / duration)
        value = int(32767 * 0.4 * math.sin(2 * math.pi * freq * t))
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

def create_explosion():
    sample_rate = 44100
    frames = int(0.2 * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        noise = random.randint(-8000, 8000)
        decay = 1 - (t / 0.2)
        value = int(noise * decay)
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

def create_rising(f1, f2, duration):
    sample_rate = 44100
    frames = int(duration * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        freq = f1 + (f2 - f1) * (t / duration)
        value = int(32767 * 0.6 * math.sin(2 * math.pi * freq * t))
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

def create_powerup():
    sample_rate = 44100
    frames = int(0.8 * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        f1 = 600 + 300 * math.sin(t * 12)
        f2 = 1200 + 200 * math.sin(t * 18)
        value = int(32767 * 0.3 * (math.sin(2 * math.pi * f1 * t) + 0.6 * math.sin(2 * math.pi * f2 * t)))
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

def create_jingle():
    sample_rate = 44100
    total_frames = int(1.0 * sample_rate)
    data = bytearray(b'\x00\x00' * total_frames)
    notes = [(523, 0.15), (659, 0.15), (784, 0.15), (1047, 0.4)]
    pos = 0
    for freq, dur in notes:
        frames = int(dur * sample_rate)
        for i in range(frames):
            if pos + i < total_frames:
                t = i / sample_rate
                value = int(32767 * 0.5 * math.sin(2 * math.pi * freq * t))
                offset = (pos + i) * 2
                data[offset:offset+2] = value.to_bytes(2, 'little', signed=True)
        pos += frames
    return pygame.mixer.Sound(buffer=data)

def create_bomb_sound():
    sample_rate = 44100
    frames = int(0.6 * sample_rate)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        freq = 100 + 800 * (1 - t / 0.6)
        noise = random.randint(-12000, 12000) * (1 - t / 0.6)
        value = int(noise + 32767 * 0.7 * math.sin(2 * math.pi * freq * t))
        value = max(-32768, min(32767, value))
        data.extend(value.to_bytes(2, 'little', signed=True))
    return pygame.mixer.Sound(buffer=data)

# Load sounds
shoot_sound = load_sound_safe("shoot.wav")
hit_sound = load_sound_safe("hit.wav")
explode_sound = load_sound_safe("explode.wav")
powerup_sound = load_sound_safe("powerup.wav")
boss_sound = load_sound_safe("boss.wav")
victory_sound = load_sound_safe("victory.wav")
levelup_sound = load_sound_safe("levelup.wav")
transform_sound = load_sound_safe("transform.wav")
bomb_sound = load_sound_safe("bomb.wav")

# Background music
music_path = ap("sounds/music.ogg")
if os.path.exists(music_path):
    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(0.9)
    except:
        pass

# ---------------- LOADERS ----------------
def load_image_safe(name, size=None):
    path = ap(name)
    if path and os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if size: img = pygame.transform.smoothscale(img, size)
            return img
        except: pass
    s = size or (64,64)
    surf = pygame.Surface(s, pygame.SRCALPHA)
    surf.fill((120,120,120,255))
    return surf

# ---------------- ASSETS ----------------
stage_img = load_image_safe("assets/stage.png", (WIDTH*3, HEIGHT))

# --- HERO FRAMES: normalize canvas so wing / frame differences don't compress or misalign frames ---
# Load raw hero frames without forcing a uniform size first (so we can inspect originals).
hero_raw = [load_image_safe(f"assets/hero{i+1}.png") for i in range(4)]

# Determine maximum original width/height and add a horizontal padding so wing sprites can overlap
orig_sizes = [img.get_size() for img in hero_raw]
max_w = max([w for w,h in orig_sizes]) if orig_sizes else 64
max_h = max([h for w,h in orig_sizes]) if orig_sizes else 64
WING_PADDING = 24  # extra horizontal pixels to allow wing span overlap
HERO_CANVAS = (max_w + WING_PADDING, max_h)

# Create consistent-sized frames by centering each raw frame on a new surface with extra width
hero_imgs = []
for i, img in enumerate(hero_raw):
    surf = pygame.Surface(HERO_CANVAS, pygame.SRCALPHA)
    x = (HERO_CANVAS[0] - img.get_width()) // 2
    y = (HERO_CANVAS[1] - img.get_height()) // 2
    surf.blit(img, (x, y))
    hero_imgs.append(surf)

# Debug print to help you spot mismatched source frames during testing (remove/comment in production)
print("hero frame original sizes:", orig_sizes, "-> normalized to:", HERO_CANVAS)

# Transform image: ensure it's not awkwardly scaled compared to normalized hero frames
hero_transform_img = load_image_safe("assets/hero_transform.png")
if hero_transform_img.get_size() != HERO_CANVAS:
    t_surf = pygame.Surface(HERO_CANVAS, pygame.SRCALPHA)
    tx = (HERO_CANVAS[0] - hero_transform_img.get_width()) // 2
    ty = (HERO_CANVAS[1] - hero_transform_img.get_height()) // 2
    t_surf.blit(hero_transform_img, (tx, ty))
    hero_transform_img = t_surf

enemy_img = pygame.transform.smoothscale(load_image_safe("assets/enemy.png", (48,48)), (64,64))

# BOSS IMAGE — FIXED!
boss_img = load_image_safe("assets/boss1.png", (140, 140))
if boss_img.get_width() < 10:
    boss_img = pygame.Surface((140, 140), pygame.SRCALPHA)
    pygame.draw.circle(boss_img, (180, 0, 180), (70, 70), 60)
    pygame.draw.circle(boss_img, (255, 100, 255), (70, 70), 60, 8)
    pygame.draw.polygon(boss_img, (255, 50, 255), [(70,10), (100,60), (70,110), (40,60)])
    pygame.draw.circle(boss_img, (255, 200, 255), (50, 50), 15)
    pygame.draw.circle(boss_img, (255, 200, 255), (90, 90), 15)

# DINO HELPER SPRITE (load default first)
dino_img = load_image_safe(DINO_SPRITE_PATH, (48, 48))
if dino_img.get_width() < 10:
    dino_img = pygame.Surface((48,48), pygame.SRCALPHA)
    pygame.draw.polygon(dino_img, (80,180,80), [(12,24),(24,12),(36,24),(24,36)])
    pygame.draw.circle(dino_img, (120,220,120), (20,20), 8)
    pygame.draw.circle(dino_img, (220,220,220), (20,20), 4)
    pygame.draw.circle(dino_img, (60,140,60), (36,20), 8)
    pygame.draw.circle(dino_img, (220,220,220), (36,20), 4)
    pygame.draw.polygon(dino_img, (150,255,150), [(12,24),(24,12),(36,24),(24,36)], 2)

# ---------------- Rune system / visuals ----------------
rune_colors = [(255,200,100), (100,200,255), (200,100,255), (255,100,100)]
def create_rune_glow(size, color, alpha=180):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*color, alpha), (size//2, size//2), size//3)
    for a in range(0, 360, 45):
        rad = radians(a)
        x1 = size//2 + int((size//4) * cos(rad))
        y1 = size//2 + int((size//4) * sin(rad))
        x2 = size//2 + int((size//3) * cos(rad + 0.3))
        y2 = size//2 + int((size//3) * sin(rad + 0.3))
        pygame.draw.line(surf, (*color, min(255, alpha+50)), (x1,y1), (x2,y2), 3)
    return surf

muzzle_imgs = [create_rune_glow(48, c) for c in rune_colors]
bullet_imgs = [create_rune_glow(24, c, 220) for c in rune_colors]
hit_imgs = [create_rune_glow(48, c, 200) for c in rune_colors]
rune_img = create_rune_glow(36, (200,180,255), 240)

# ---------------- BOMB ANIMATION ----------------
bomb_frames = []
for i in range(8):
    surf = pygame.Surface((60,60), pygame.SRCALPHA)
    t = i / 7
    radius = 10 + int(15 * t)
    alpha = int(255 * (1 - t))
    color = (255, int(150*t), int(50*t), alpha)
    pygame.draw.circle(surf, color, (30,30), radius)
    for j in range(6):
        ang = j * 60 + i * 15
        rad = radians(ang)
        x1 = 30 + int(20 * cos(rad))
        y1 = 30 + int(20 * sin(rad))
        x2 = 30 + int(35 * cos(rad))
        y2 = 30 + int(35 * sin(rad))
        pygame.draw.line(surf, color, (x1,y1), (x2,y2), 3)
    bomb_frames.append(surf)
bomb_anim_timer = 0.0
bomb_anim_index = 0

# ---------------- SUB WEAPON SPRITES ----------------
def create_sub_sprite(typ):
    surf = pygame.Surface((48,48), pygame.SRCALPHA)
    if typ == "missile":
        pygame.draw.polygon(surf, (200,50,50), [(24,10), (38,24), (24,38), (10,24)])
        pygame.draw.polygon(surf, (255,100,100), [(24,10), (38,24), (24,38), (10,24)], 3)
        pygame.draw.line(surf, (255,200,50), (10,24), (0,24), 4)
    elif typ == "laser":
        pygame.draw.line(surf, (0,255,255), (10,24), (38,24), 8)
        pygame.draw.line(surf, (100,255,255), (10,24), (38,24), 4)
        pygame.draw.circle(surf, (0,200,255), (38,24), 6)
    elif typ == "lightning":
        points = [(10,10), (18,18), (14,26), (22,34), (18,42)]
        pygame.draw.lines(surf, (200,200,255), False, points, 5)
        pygame.draw.lines(surf, (255,255,100), False, points, 2)
    return surf

sub_imgs = {}
for typ in sub_weapons:
    path = sub_sprite_paths.get(typ)
    img = load_image_safe(path, (48,48))
    if img.get_width() < 10:
        img = create_sub_sprite(typ)
    sub_imgs[typ] = img

# ---------------- PARTICLE SYSTEM ----------------
particles = []
def create_particles(x, y, count=15, color=(255,200,100), speed=8, life=0.8, size=4, gravity=0.3, spread=360):
    for _ in range(count):
        angle = random.uniform(0, spread)
        vel = random.uniform(speed * 0.5, speed)
        vx = math.cos(math.radians(angle)) * vel
        vy = math.sin(math.radians(angle)) * vel
        particles.append({
            "x": x, "y": y, "vx": vx, "vy": vy,
            "life": life, "max_life": life, "color": color, "size": size, "gravity": gravity
        })

def update_particles(dt):
    for p in particles[:]:
        p["vy"] += p["gravity"]
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["life"] -= dt
        if p["life"] <= 0:
            particles.remove(p)

def draw_particles():
    for p in particles:
        alpha = int(255 * (p["life"] / p["max_life"]))
        size = max(1, int(p["size"] * (p["life"] / p["max_life"])))
        color = (*p["color"], alpha)
        s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (size, size), size)
        screen.blit(s, (int(p["x"] - size) + shake_offset[0], int(p["y"] - size) + shake_offset[1]))

# ---------------- GAME STATE ----------------
scene = "title"
selected_hero = 0
# Player now has shield, speed_level and damage_level for upgraded power-ups
player = {"x":140.0, "y":HEIGHT/2, "hp":100, "level":1, "exp":0, "last_shot":0.0, "transformed":False,
          "shield": 0, "shield_max": 30, "speed_level": 1, "damage_level": 1}
bullets, enemies, effects, float_pops, powerups = [], [], [], [], []
boss = None
score = 0
scroll_x, scroll_speed = 0.0, 3.0
enemy_spawn_timer = time.time()
shake_timer = 0.0
shake_offset = (0,0)

# ---------------- HELPERS ----------------
def clamp(v, lo, hi): return max(lo, min(hi, v))
def now(): return time.time()
def add_float_pop(x, y, txt, color=(255,255,150)):
    float_pops.append({"x":x, "y":y, "txt":txt, "t":now(), "dur":0.6, "color":color})

# ---------------- LEVEL SYSTEM ----------------
def gain_exp(amount):
    global helper_count, helper_spawn_timer
    player["exp"] += amount
    while player["exp"] >= player["level"] * 100 and player["level"] < MAX_LEVEL:
        player["level"] += 1
        player["exp"] -= (player["level"]-1) * 100
        add_float_pop(player["x"], player["y"]-40, f"LEVEL {player['level']}!", (100,255,100))
        if levelup_sound: levelup_sound.play()
        if player["level"] == TRANSFORM_LEVEL and not player["transformed"]:
            player["transformed"] = True
            effects.append({"type":"transform", "x":player["x"], "y":player["y"], "t":now(), "dur":1.0})
            create_particles(player["x"], player["y"], count=30, color=(100,200,255), speed=9, life=1.0, spread=360)
            if transform_sound: transform_sound.play()

        # Grant a DINO helper every 10 levels (10, 20, 30, ...) up to MAX_HELPERS
        if player["level"] % 10 == 0 and helper_count < MAX_HELPERS:
            helper_count += 1
            idx = len(helpers)
            helpers.append({
                "offset_x": -60 - 35 * idx,
                "offset_y": 0,
                "last_mimic": 0.0,
                "mimic_delay": 0.08 + 0.06 * idx,
                "x": player["x"],
                "y": player["y"],
                "chain_offset": (-60 - 30 * idx, 0)
            })
            helper_spawn_timer = now()
            add_float_pop(player["x"], player["y"] - 20, f"DINO HELPER #{helper_count} ACQUIRED!", (100,255,100))
            if powerup_sound: powerup_sound.play()

# ---------------- BOMB SKILL ----------------
def activate_bomb():
    global bomb_cooldown, player_invulnerable, invul_timer, bomb_flash
    global bomb_anim_timer, bomb_anim_index, shake_timer
    if bomb_cooldown > 0: return
    bomb_cooldown = BOMB_COOLDOWN_TIME
    player_invulnerable = True
    invul_timer = BOMB_INVUL_TIME
    bomb_flash = 0.3
    bomb_anim_timer = now()
    bomb_anim_index = 0
    cleared = 0
    for b in bullets[:]:
        if b.get("is_enemy"):
            bullets.remove(b)
            create_particles(b["x"], b["y"], 8, (255,200,50), 10, 0.6)
            cleared += 1
    if cleared:
        add_float_pop(WIDTH//2, HEIGHT//2, f"CLEARED {cleared} BULLETS!", (255,215,0))
    for _ in range(120):
        create_particles(player["x"], player["y"], 1, (255,100,0), 22, 2.0, 12, 0.5, 360)
    if bomb_sound: bomb_sound.play()
    shake_timer = now() + 0.4

# ---------------- SUB WEAPON ----------------
def player_sub_shoot():
    global sub_cooldown
    if sub_cooldown > 0: return
    sub_cooldown = SUB_COOLDOWN_TIME
    if sub_weapon == "missile":
        bullets.append({
            "x": player["x"]+36, "y": player["y"], "vx": 30, "vy": 0,
            "img": sub_imgs["missile"], "glow": True, "damage": 15,
            "type": "missile", "homing": True, "target": None
        })
        create_particles(player["x"]+40, player["y"], 8, (255,150,50), 10, 0.4)
    elif sub_weapon == "laser":
        bullets.append({
            "x": player["x"]+40, "y": player["y"], "vx": 90, "vy": 0,
            "img": sub_imgs["laser"], "glow": True, "damage": 8,
            "type": "laser", "pierce": 99
        })
        effects.append({"type":"laser_beam", "x":player["x"]+40, "y":player["y"], "t":now(), "dur":0.3})
    elif sub_weapon == "lightning":
        targets = enemies[:]
        if boss: targets.append(boss)
        if targets:
            start = {"x": player["x"]+40, "y": player["y"]}
            chain_all_lightning(start, targets, 20)

def chain_all_lightning(start, targets, damage):
    if not targets: return
    current = start
    for target in targets:
        effects.append({
            "type":"lightning", "x1":current["x"], "y1":current["y"],
            "x2":target["x"], "y2":target["y"], "t":now(), "dur":0.15
        })
        create_particles(target["x"], target["y"], 15, (200,200,255), 12, 0.6)
        target["hp"] -= damage
        current = target
    if shoot_sound: shoot_sound.play()

# ---------------- SPAWN ----------------
def spawn_enemy():
    y = random.randint(80, HEIGHT-80)
    speed = random.uniform(ENEMY_MIN_SPEED, ENEMY_MAX_SPEED)
    # firing multiplier scales down with level so fire_delay shortens (enemies fire faster at higher levels)
    level = clamp(player.get("level", 1), 1, MAX_LEVEL)
    fire_mult = max(ENEMY_FIRE_MIN_MULT, 1.0 - (level - 1) * ENEMY_RATE_SCALE_PER_LEVEL)
    enemies.append({
        "x": WIDTH + 50, "y": y, "target_y": y, "speed": speed,
        "hp": 2 + random.randint(0, 3), "w": 64, "h": 64,
        "last_shot": 0.0, "fire_delay": random.uniform(1.8, 3.0) * fire_mult,
        "type": random.choice(["normal", "shooter", "dodger"]),
        "dodge_timer": 0.0
    })

def spawn_boss():
    global boss
    boss = {
        "x": WIDTH + 150, "y": HEIGHT//2, "hp": 50, "max_hp": 50,
        "speed": 2.5, "last_shot": now(), "fire_delay": 1.0,
        "type": "normal"
    }
    add_float_pop(WIDTH//2, 100, "BOSS INCOMING!", (255,0,0))
    if boss_sound: boss_sound.play()

def spawn_boss2():
    global boss
    boss = {
        "x": WIDTH + 150, "y": HEIGHT//2, "hp": 80, "max_hp": 80,
        "speed": 3.0, "last_shot": now(), "fire_delay": 0.6,
        "phase": "normal", "transformed": False, "dodge_timer": 0.0, "type": "smart"
    }
    add_float_pop(WIDTH//2, 100, "SMART BOSS!", (255,0,255))
    if boss_sound: boss_sound.play()

def spawn_boss3():
    global boss
    boss = {
        "x": WIDTH + 200, "y": HEIGHT//2, "hp": 200, "max_hp": 200,
        "speed": 1.8, "last_shot": now(), "fire_delay": 0.5,
        "phase": "summon", "transformed": False, "dodge_timer": 0.0,
        "type": "apocalypse", "minions": 0, "laser_timer": 0.0
    }
    add_float_pop(WIDTH//2, 80, "APOCALYPSE BOSS!", (255,100,255))
    add_float_pop(WIDTH//2, 110, "15000 PTS", (255,255,0))
    if boss_sound: boss_sound.play()

def spawn_boss4():
    global boss
    boss = {
        "x": WIDTH + 200, "y": HEIGHT//2, "hp": 400, "max_hp": 400,
        "speed": 2.0, "last_shot": now(), "fire_delay": 0.4,
        "phase": "enter", "transformed": False, "dodge_timer": 0.0,
        "type": "nexus", "minions": 0, "teleport_timer": 0.0, "reflect": False
    }
    add_float_pop(WIDTH//2, 70, "NEXUS BOSS!", (255,50,255))
    add_float_pop(WIDTH//2, 100, "30,000 PTS", (255,215,0))
    add_float_pop(WIDTH//2, 130, "REFLECTS BULLETS!", (255,100,100))
    if boss_sound: boss_sound.play()

# ---------------- SHOOT ----------------
def player_shoot():
    global transform_anim_timer, transform_anim_index, transform_sheet_cooldown
    nowt = now()
    delay = 0.12 / (1 + player["level"] * 0.02)
    if nowt - player["last_shot"] < delay: return
    player["last_shot"] = nowt
    row = selected_hero
    mu = muzzle_imgs[row]
    effects.append({"type":"muzzle", "x":player["x"]+40, "y":player["y"], "img":mu, "t":nowt, "dur":0.1, "glow":True})
    if shoot_sound: shoot_sound.play()

    # If transformed: fire a bullet-sheet (fan/spread) but only if sheet cooldown allows
    if player.get("transformed", False):
        if transform_sheet_cooldown > 0:
            # sheet still on cooldown: fallback to a single-shot to avoid wasted input
            shots = 1
            base_damage_from_level = 1 + (player["level"]//10)
            damage_level = player.get("damage_level", 1)
            for i in range(shots):
                angle = 0
                vx = BULLET_SPEED * cos(angle)
                vy = BULLET_SPEED * sin(angle)
                bullets.append({
                    "x": player["x"]+36, "y": player["y"], "vx": vx, "vy": vy,
                    "img": bullet_imgs[row], "glow": True,
                    "damage": base_damage_from_level + max(0, damage_level - 1)
                })
            return
        # allowed to fire sheet
        count = max(1, TRANSFORM_BULLET_SHEET_COUNT)
        spread = float(TRANSFORM_BULLET_SPREAD_DEG)
        base_damage_from_level = 1 + (player["level"]//10)
        damage_level = player.get("damage_level", 1)
        base_damage = base_damage_from_level + max(0, damage_level - 1)
        base_damage = int(base_damage * TRANSFORM_BULLET_DAMAGE_MULT)

        for i in range(count):
            if count == 1:
                angle_deg = 0.0
            else:
                angle_deg = -spread/2.0 + (spread * (i / (count - 1)))
            ang = radians(angle_deg)
            vx = BULLET_SPEED * cos(ang) * TRANSFORM_BULLET_SPEED_MULT
            vy = BULLET_SPEED * sin(ang) * TRANSFORM_BULLET_SPEED_MULT
            # choose an image from the transform atlas if available
            if transform_bullet_imgs:
                img_choice = transform_bullet_imgs[i % len(transform_bullet_imgs)]
            else:
                img_choice = bullet_imgs[row]
            bullets.append({
                "x": player["x"]+36, "y": player["y"], "vx": vx, "vy": vy,
                "img": img_choice, "glow": True,
                "damage": base_damage
            })
        # set sheet cooldown to prevent immediate re-fire
        transform_sheet_cooldown = TRANSFORM_SHEET_COOLDOWN
    else:
        shots = 1 + (player["level"] >= 10)
        base_damage_from_level = 1 + (player["level"]//10)
        # incorporate damage_level (max 10)
        damage_level = player.get("damage_level", 1)
        for i in range(shots):
            angle = radians(-10 + 20*i) if shots > 1 else 0
            vx = BULLET_SPEED * cos(angle)
            vy = BULLET_SPEED * sin(angle)
            bullets.append({
                "x": player["x"]+36, "y": player["y"], "vx": vx, "vy": vy,
                "img": bullet_imgs[row], "glow": True,
                "damage": base_damage_from_level + max(0, damage_level - 1)
            })

def enemy_shoot(e):
    nowt = now()
    if nowt - e["last_shot"] < e["fire_delay"]: return
    dx = player["x"] - e["x"]
    dy = player["y"] - e["y"]
    dist = max(1, hypot(dx, dy))
    base_vx = (dx/dist) * ENEMY_BULLET_SPEED
    base_vy = (dy/dist) * ENEMY_BULLET_SPEED
    if e["type"] == "shooter":
        for angle in [-15, 0, 15]:
            rad = math.atan2(base_vy, base_vx) + radians(angle)
            vx = math.cos(rad) * ENEMY_BULLET_SPEED
            vy = math.sin(rad) * ENEMY_BULLET_SPEED
            bullets.append({
                "x": e["x"]-20, "y": e["y"], "vx": vx, "vy": vy,
                "img": bullet_imgs[2], "glow": True, "is_enemy": True, "damage": 5  
            })
    elif e["type"] == "dodger":
        bullets.append({
            "x": e["x"]-20, "y": e["y"], "vx": base_vx, "vy": base_vy,
            "img": bullet_imgs[3], "glow": True, "is_enemy": True, "damage": 10
        })
        e["dodge_timer"] = now() + 0.3
    else:
        bullets.append({
            "x": e["x"]-20, "y": e["y"], "vx": base_vx, "vy": base_vy,
            "img": bullet_imgs[3], "glow": True, "is_enemy": True, "damage": 10
        })
    e["last_shot"] = nowt
    # after shooting, reset fire_delay scaled by player's level (so subsequent shots come faster at higher levels)
    level = clamp(player.get("level", 1), 1, MAX_LEVEL)
    fire_mult = max(ENEMY_FIRE_MIN_MULT, 1.0 - (level - 1) * ENEMY_RATE_SCALE_PER_LEVEL)
    e["fire_delay"] = random.uniform(1.5, 3.0) * fire_mult

# ---------------- POWER-UPS ----------------
# Updated: Speed and Damage levels capped at 10.
# Added: "rune" powerup — grants 1000 EXP and increases/refills shield.
# Runes move randomly across the screen and expire after 10s if not collected.
powerup_colors = {"hp": (0,255,0), "speed": (255,255,0), "damage": (255,100,255), "rune": (200,180,255)}
powerup_imgs = {}
for typ, col in powerup_colors.items():
    surf = pygame.Surface((40,40), pygame.SRCALPHA)
    pygame.draw.circle(surf, col, (20,20), 18)
    pygame.draw.circle(surf, (255,255,255), (20,20), 18, 3)
    font_small = pygame.font.SysFont("arial", 16, bold=True)
    if typ == "rune":
        txt = font_small.render("R", True, (0,0,0))
    else:
        txt = font_small.render(typ.upper()[0], True, (0,0,0))
    surf.blit(txt, (20 - txt.get_width()//2, 20 - txt.get_height()//2))
    powerup_imgs[typ] = surf

# ---------------- UPDATE ENTITIES ----------------
def update_entities(dt):
    global score, boss, shake_timer, enemy_spawn_timer, PLAYER_SPEED
    global bomb_cooldown, player_invulnerable, invul_timer, bomb_flash
    global bomb_anim_timer, bomb_anim_index, sub_cooldown
    global helper_count, helper_spawn_timer, transform_sheet_cooldown

    # COOLDOWNS
    if bomb_cooldown > 0:
        bomb_cooldown -= dt
    if player_invulnerable:
        invul_timer -= dt
        if invul_timer <= 0:
            player_invulnerable = False
    if bomb_cooldown > 0 and now() - bomb_anim_timer > 0.08:
        bomb_anim_timer = now()
        bomb_anim_index = (bomb_anim_index + 1) % len(bomb_frames)
    if sub_cooldown > 0:
        sub_cooldown -= dt

    # decrement transform sheet cooldown so it recovers over time
    if transform_sheet_cooldown > 0:
        transform_sheet_cooldown = max(0.0, transform_sheet_cooldown - dt)

    # BOSS AUTO-SPAWN
    if not boss:
        if score >= BOSS_SPAWN_SCORE and (score % BOSS_SPAWN_SCORE) < 50:
            spawn_boss()
        elif score >= BOSS2_SPAWN_SCORE and (score % BOSS2_SPAWN_SCORE) < 50:
            spawn_boss2()
        elif score >= BOSS3_SPAWN_SCORE and (score % BOSS3_SPAWN_SCORE) < 50:
            spawn_boss3()
        elif score >= BOSS4_SPAWN_SCORE and (score % BOSS4_SPAWN_SCORE) < 50:
            spawn_boss4()

    # ENEMY SPAWNING (scaled by player level)
    # spawn interval reduces as player level increases (higher spawn rate at higher levels)
    level = clamp(player.get("level", 1), 1, MAX_LEVEL)
    level_multiplier = max(0.3, 1.0 - (level - 1) * ENEMY_RATE_SCALE_PER_LEVEL)
    spawn_interval = max(ENEMY_SPAWN_MIN_INTERVAL, ENEMY_SPAWN_BASE_INTERVAL * level_multiplier)

    if time.time() - enemy_spawn_timer > spawn_interval:
        enemy_spawn_timer = time.time()
        spawn_enemy()

    # POWER-UP CHANCE (including occasional rune spawn)
    if random.random() < 0.003 and len(powerups) < 3:
        powerups.append({
            "x": WIDTH + 50,
            "y": random.randint(60, HEIGHT - 60),
            "type": random.choice(["hp", "speed", "damage"])
        })
    # spawn runes more rarely
    if random.random() < 0.001 and len(powerups) < 4:
        # rune moves randomly and lives for 10s
        powerups.append({
            "x": random.randint(80, WIDTH-80),
            "y": random.randint(80, HEIGHT-80),
            "vx": random.uniform(-120,120)/60.0,
            "vy": random.uniform(-120,120)/60.0,
            "t": now(),
            "type": "rune",
            "life": 10.0
        })

    # DINO HELPER AUTO-SPAWN
    if helper_count > len(helpers) and now() - helper_spawn_timer > 8.0:
        helper_spawn_timer = now()
        helpers.append({
            "offset_x": -60 - 35 * len(helpers),
            "offset_y": 0,
            "last_mimic": 0.0,
            "mimic_delay": 0.08 + 0.06 * len(helpers),
            "x": player["x"],
            "y": player["y"],
            "chain_offset": (-60 - 30 * len(helpers), 0)
        })
        add_float_pop(WIDTH // 2, HEIGHT // 2,
                      f"DINO HELPER #{len(helpers)}", (100, 255, 100))

    # BOSS MOVEMENT & ATTACK
    if boss:
        if boss["x"] > WIDTH - 300:
            boss["x"] -= boss["speed"]
        else:
            boss["x"] = WIDTH - 300

        if now() - boss["last_shot"] > boss["fire_delay"]:
            boss["last_shot"] = now()
            if boss["type"] == "normal":
                for angle in [-30, -15, 0, 15, 30]:
                    rad = radians(angle)
                    vx = -ENEMY_BULLET_SPEED * 0.8 * cos(rad)
                    vy = ENEMY_BULLET_SPEED * 0.8 * sin(rad)
                    bullets.append({
                        "x": boss["x"] - 50, "y": boss["y"],
                        "vx": vx, "vy": vy,
                        "img": bullet_imgs[1], "glow": True,
                        "is_enemy": True, "damage": 15
                    })
            elif boss["type"] == "smart":
                dx = player["x"] - boss["x"]
                dy = player["y"] - boss["y"]
                dist = max(1, hypot(dx, dy))
                base_vx = (dx/dist) * ENEMY_BULLET_SPEED * 0.9
                base_vy = (dy/dist) * ENEMY_BULLET_SPEED * 0.9
                for angle in [-20, -10, 0, 10, 20]:
                    rad = math.atan2(base_vy, base_vx) + radians(angle)
                    vx = cos(rad) * ENEMY_BULLET_SPEED * 0.9
                    vy = sin(rad) * ENEMY_BULLET_SPEED * 0.9
                    bullets.append({
                        "x": boss["x"] - 50, "y": boss["y"] + random.randint(-20,20),
                        "vx": vx, "vy": vy,
                        "img": bullet_imgs[2], "glow": True,
                        "is_enemy": True, "damage": 18
                    })
            elif boss["type"] == "apocalypse":
                if random.random() < 0.3:
                    enemies.append({
                        "x": boss["x"], "y": boss["y"] + random.randint(-100,100),
                        "target_y": boss["y"], "speed": 4.0,
                        "hp": 3, "w": 64, "h": 64,
                        "last_shot": 0.0, "fire_delay": 2.0,
                        "type": "shooter"
                    })
                if boss.get("laser_timer", 0) <= 0:
                    boss["laser_timer"] = now() + 2.0
                    effects.append({"type": "laser_warning", "y": player["y"], "t": now(), "dur": 1.5})
            elif boss["type"] == "nexus":
                if random.random() < 0.02:
                    boss["reflect"] = True
                    create_particles(boss["x"], boss["y"], 20, (255,100,255), 8, 0.8)
                if now() - boss.get("teleport_timer", 0) > 8.0:
                    boss["teleport_timer"] = now()
                    boss["x"] = WIDTH + 100
                    create_particles(boss["x"], boss["y"], 40, (200,50,255), 15, 1.2)

    # BULLET MOVEMENT & COLLISION
    for b in bullets[:]:
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        if (b["x"] < -100 or b["x"] > WIDTH + 100 or
            b["y"] < -100 or b["y"] > HEIGHT + 100):
            bullets.remove(b)
            continue

        if not b.get("is_enemy"):
            hit = False
            for e in enemies[:]:
                if (abs(b["x"] - e["x"]) < 48 and abs(b["y"] - e["y"]) < 48):
                    e["hp"] -= b.get("damage", 1)
                    hit = True
                    if e["hp"] <= 0:
                        enemies.remove(e)
                        score += 100
                        gain_exp(10)
                        create_particles(e["x"], e["y"], 12, (255, 200, 50), 10, 0.6)
                        if explode_sound: explode_sound.play()
            if boss and (abs(b["x"] - boss["x"]) < 80 and abs(b["y"] - boss["y"]) < 80):
                boss["hp"] -= b.get("damage", 1)
                hit = True
                create_particles(b["x"], b["y"], 10, (255, 255, 200), 10, 0.5)
                effects.append({"type": "hit_flash", "t": now(), "dur": 0.1})
                if hit_sound: hit_sound.play()
            if hit:
                bullets.remove(b)
                create_particles(b["x"], b["y"], 6, (255, 255, 100), 6, 0.3)
        else:
            # Enemy bullet hits player: shield absorbs first, then hp
            if (abs(b["x"] - player["x"]) < 40 and
                abs(b["y"] - player["y"]) < 40 and
                not player_invulnerable):
                dmg = b.get("damage", 10)
                shield = player.get("shield", 0)
                if shield > 0:
                    taken_by_shield = min(shield, dmg)
                    player["shield"] -= taken_by_shield
                    dmg -= taken_by_shield
                    create_particles(b["x"], b["y"], 8, (100,200,255), 6, 0.4)  # shield hit effect
                if dmg > 0:
                    player["hp"] -= dmg
                bullets.remove(b)
                create_particles(b["x"], b["y"], 8, (255, 100, 0), 8, 0.4)
                if hit_sound: hit_sound.play()

    # ENEMY MOVEMENT
    for e in enemies[:]:
        e["x"] -= e["speed"]
        if random.random() < 0.012:
            enemy_shoot(e)
        if e["x"] < -100:
            enemies.remove(e)

    # BOSS DEATH
    if boss and boss["hp"] <= 0:
        reward = 5000 if boss["type"] == "nexus" else 2500 if boss["type"] == "apocalypse" else 1500 if boss["type"] == "smart" else 1000
        if victory_sound: victory_sound.play()
        gain_exp(1000 if boss["type"] == "nexus" else 500)
        score += reward
        # NOTE: helper acquisition moved to level-up rewards (every 10 levels).
        # Keep boss points & celebratory particles but do NOT auto-grant a helper here.
        add_float_pop(boss["x"], boss["y"] - 50, f"+{reward} PTS", (255, 215, 0))
        for _ in range(12):
            create_particles(boss["x"] + random.randint(-80, 80), boss["y"] + random.randint(-80, 80), 40, (255, 50, 50), 18, 2.5, 6, 0.6)
        boss = None

    # POWERUP MOVEMENT & PICKUP
    for p in powerups[:]:
        # moving runes have vx/vy and lifetime
        if p.get("type") == "rune":
            # move
            p["x"] += p.get("vx", 0) * dt * FPS
            p["y"] += p.get("vy", 0) * dt * FPS
            # bounce
            if p["x"] < 40 or p["x"] > WIDTH - 40:
                p["vx"] *= -1
            if p["y"] < 40 or p["y"] > HEIGHT - 40:
                p["vy"] *= -1
            # expire after life seconds
            if now() - p.get("t", now()) > p.get("life", 10):
                powerups.remove(p)
                continue

        # check pickup by player
        if abs(p["x"] - player["x"]) < 40 and abs(p["y"] - player["y"]) < 40:
            typ = p.get("type")
            if typ == "hp":
                player["hp"] = min(100, player["hp"] + 30)
                add_float_pop(player["x"], player["y"] - 20, "+30 HP", (0,255,0))
            elif typ == "speed":
                # increase speed_level up to 10
                sl = player.get("speed_level", 1)
                if sl < 10:
                    player["speed_level"] = sl + 1
                    add_float_pop(player["x"], player["y"] - 20, f"SPEED LVL {player['speed_level']}", (255,255,0))
                else:
                    add_float_pop(player["x"], player["y"] - 20, "SPEED MAX", (200,200,0))
            elif typ == "damage":
                dl = player.get("damage_level", 1)
                if dl < 10:
                    player["damage_level"] = dl + 1
                    add_float_pop(player["x"], player["y"] - 20, f"DAMAGE LVL {player['damage_level']}", (255,100,255))
                else:
                    add_float_pop(player["x"], player["y"] - 20, "DAMAGE MAX", (200,100,200))
            elif typ == "rune":
                # runes give 1000 EXP and increase shield_max by +10 (cap 100) and refill shield
                gain_exp(1000)
                old_shield_max = player.get("shield_max", 30)
                new_shield_max = min(100, old_shield_max + 10)
                player["shield_max"] = new_shield_max
                player["shield"] = new_shield_max  # refill every rune
                add_float_pop(player["x"], player["y"] - 20, "+1000 EXP + SHIELD", (200,180,255))
                if powerup_sound: powerup_sound.play()
            # remove powerup after pickup
            if p in powerups:
                powerups.remove(p)

    update_particles(dt)

# ---------------- DINO-CHAIN / CUSTOM DINO INTEGRATION ----------------
def _synth_dino_sprite(size=(48,48)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w,h = size
    scale = min(w,h) / 48.0
    pygame.draw.ellipse(surf, (80,180,80), (int(6*scale), int(10*scale), int(30*scale), int(22*scale)))
    pygame.draw.circle(surf, (120,220,120), (int(36*scale), int(20*scale)), int(7*scale))
    pygame.draw.circle(surf, (255,255,255), (int(37*scale), int(18*scale)), max(1, int(2*scale)))
    pygame.draw.polygon(surf, (60,160,60), [
        (int(8*scale), int(18*scale)),
        (int(18*scale), int(6*scale)),
        (int(28*scale), int(18*scale))
    ])
    pygame.draw.polygon(surf, (60,160,60), [
        (int(8*scale), int(30*scale)),
        (int(18*scale), int(42*scale)),
        (int(28*scale), int(30*scale))
    ])
    pygame.draw.polygon(surf, (100,220,100), [
        (int(10*scale), int(20*scale)),
        (int(18*scale), int(10*scale)),
        (int(26*scale), int(20*scale))
    ], 2)
    return surf

def install_dino_chain(globals_dict, custom_path=CUSTOM_DINO_PATH, size=(48,48), wing_padding=12):
    """
    Install custom dino sprite and dino_chain_update into provided globals_dict.
    Call this after assets are loaded so load_image_safe is available.
    """
    try:
        # load custom sprite if present
        dino_img_local = None
        custom_full = ap(custom_path)
        if custom_path and os.path.exists(custom_full):
            if 'load_image_safe' in globals_dict and callable(globals_dict['load_image_safe']):
                try:
                    dino_img_local = globals_dict['load_image_safe'](custom_path, size)
                except Exception:
                    dino_img_local = None
            else:
                try:
                    img = pygame.image.load(custom_full).convert_alpha()
                    dino_img_local = pygame.transform.smoothscale(img, size)
                except Exception:
                    dino_img_local = None

        # fallback: prefer existing dino_img if reasonable
        if dino_img_local is None and 'dino_img' in globals_dict:
            try:
                existing = globals_dict['dino_img']
                if hasattr(existing, 'get_width') and existing.get_width() >= 8:
                    dino_img_local = pygame.transform.smoothscale(existing, size)
            except Exception:
                dino_img_local = None

        if dino_img_local is None:
            dino_img_local = _synth_dino_sprite(size)

        # write into globals so main draw uses it
        globals_dict['dino_img'] = dino_img_local

        # ensure helpers if present have chain offsets and x/y
        if 'helpers' in globals_dict:
            for i, h in enumerate(globals_dict['helpers']):
                h.setdefault('chain_index', i)
                h.setdefault('chain_offset', (-60 - 30 * i, 0))
                if 'player' in globals_dict and isinstance(globals_dict['player'], dict):
                    h.setdefault('x', globals_dict['player'].get('x', 0))
                    h.setdefault('y', globals_dict['player'].get('y', 0))
                else:
                    h.setdefault('x', h.get('x', 0))
                    h.setdefault('y', h.get('y', 0))

        # define chain update
        def dino_chain_update(player_obj, helpers_list, lerp_speed=0.18):
            if not helpers_list:
                return
            for i, h in enumerate(helpers_list):
                try:
                    if i == 0:
                        c_off = h.get('chain_offset')
                        if c_off is None:
                            tx = player_obj.get('x', 0) + h.get('offset_x', -60)
                            ty = player_obj.get('y', 0) + h.get('offset_y', 0)
                        else:
                            tx = player_obj.get('x', 0) + c_off[0]
                            ty = player_obj.get('y', 0) + c_off[1]
                    else:
                        prev = helpers_list[i-1]
                        tx = prev.get('x', player_obj.get('x', 0))
                        ty = prev.get('y', player_obj.get('y', 0))
                    mult = h.get('lerp_mult', 0.2)
                    effective_speed = lerp_speed * mult
                    h['x'] += (tx - h.get('x', tx)) * effective_speed
                    h['y'] += (ty - h.get('y', ty)) * effective_speed
                except Exception:
                    traceback.print_exc()
                    continue

        globals_dict['dino_chain_update'] = dino_chain_update
        # convenience initializer
        def dino_chain_ensure(globals_inner):
            if 'helpers' in globals_inner and 'player' in globals_inner:
                for i, h in enumerate(globals_inner['helpers']):
                    h.setdefault('chain_index', i)
                    h.setdefault('chain_offset', (-60 - 30 * i, 0))
                    h.setdefault('x', globals_inner['player'].get('x', 0))
                    h.setdefault('y', globals_inner['player'].get('y', 0))
        globals_dict['dino_chain_ensure'] = dino_chain_ensure

        return True
    except Exception:
        traceback.print_exc()
        return False

# Call the installer now so dino_img and dino_chain_update are available
install_dino_chain(globals(), custom_path=CUSTOM_DINO_PATH, size=(48,48), wing_padding=12)

# ---------------- DRAW ----------------
def draw_scene_game():
    global scroll_x, bomb_flash, transform_anim_timer, transform_anim_index
    if stage_img:
        w = stage_img.get_width()
        scroll_x = (scroll_x + scroll_speed) % w
        x = -int(scroll_x)
        while x < WIDTH:
            screen.blit(stage_img, (x + shake_offset[0], shake_offset[1]))
            x += w
    else:
        screen.fill((10,20,40))

    if bomb_flash > 0:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 200, 100, int(255 * bomb_flash)))
        screen.blit(overlay, (0, 0))
        bomb_flash = max(0, bomb_flash - 0.02)

    for b in bullets:
        img = b.get("img")
        bx = int(b["x"]) + shake_offset[0]
        by = int(b["y"]) + shake_offset[1]
        if img:
            pulse = 1.0 + 0.2 * sin(now() * 12)
            glow = pygame.transform.smoothscale(img, (int(img.get_width()*pulse), int(img.get_height()*pulse)))
            glow.set_alpha(100)
            screen.blit(glow, (bx - glow.get_width()//2, by - glow.get_height()//2))
            screen.blit(img, (bx - img.get_width()//2, by - img.get_height()//2))

    for e in enemies:
        screen.blit(enemy_img, (int(e["x"]-32) + shake_offset[0], int(e["y"]-32) + shake_offset[1]))

    # draw powerups (including moving runes)
    for p in powerups:
        img = powerup_imgs.get(p.get("type"), None)
        px = int(p["x"]) + shake_offset[0]
        py = int(p["y"]) + shake_offset[1]
        if p.get("type") == "rune":
            # draw rune glow (larger)
            ri = rune_img
            screen.blit(ri, (px - ri.get_width()//2, py - ri.get_height()//2))
        elif img:
            screen.blit(img, (px - img.get_width()//2, py - img.get_height()//2))

    for p in powerups:
        # optional tiny float label for runes remaining time
        if p.get("type") == "rune":
            remaining = int(max(0, p.get("life", 10) - (now() - p.get("t", now()))))
            txt = font.render(f"{remaining}s", True, (200,200,255))
            screen.blit(txt, (int(p["x"]) - txt.get_width()//2 + shake_offset[0], int(p["y"]) + 22 + shake_offset[1]))

    for p in powerups:
        pass  # already drawn above

    for p in powerups:
        pass

    for e in enemies:
        pass  # already drawn above

    if boss:
        screen.blit(boss_img, (int(boss["x"]-70) + shake_offset[0], int(boss["y"]-70) + shake_offset[1]))
        bar_w = 120
        hp_ratio = boss["hp"] / boss["max_hp"]
        pygame.draw.rect(screen, (100,0,0), (boss["x"]-60, boss["y"]-80, bar_w, 8))
        pygame.draw.rect(screen, (0,255,0), (boss["x"]-60, boss["y"]-80, bar_w*hp_ratio, 8))

    # Choose hero image: animated if transformed (3-frame), fallback to hero_transform_img
    try:
        if player.get("transformed", False) and transform_frames:
            if len(transform_frames) > 1 and now() - transform_anim_timer > TRANSFORM_ANIM_INTERVAL:
                transform_anim_timer = now()
                transform_anim_index = (transform_anim_index + 1) % len(transform_frames)
            img = transform_frames[transform_anim_index]
        else:
            img = hero_imgs[selected_hero]
    except Exception:
        img = hero_transform_img if player.get("transformed", False) else hero_imgs[selected_hero]

    # draw hero, applying visual-only vertical offset for transform bobbing if set
    draw_y = int(player.get("y", 0) + transform_draw_offset)
    if player_invulnerable and int(now() * 10) % 2 == 0:
        pass
    else:
        screen.blit(img, (int(player["x"] - img.get_width()//2) + shake_offset[0],
                           int(draw_y - img.get_height()//2) + shake_offset[1]))

    # DRAW DINO HELPERS (CHAINED if available)
    for h in helpers:
        pulse = 1.0 + 0.15 * sin(now() * 10)
        scaled = pygame.transform.smoothscale(dino_img, (int(48*pulse), int(48*pulse)))
        screen.blit(scaled, (int(h["x"] - 24) + shake_offset[0], int(h["y"] - 24) + shake_offset[1]))

    draw_particles()

    for ef in effects[:]:
        elapsed = now() - ef["t"]
        if elapsed > ef["dur"]:
            effects.remove(ef)
            continue
        if ef["type"] == "transform":
            alpha = int(255 * (1 - elapsed/ef["dur"]))
            s = pygame.Surface((200,200), pygame.SRCALPHA)
            s.fill((255,255,100,alpha))
            pygame.draw.circle(s, (255,255,200,alpha), (100,100), 80 + int(elapsed*100))
            screen.blit(s, (ef["x"]-100, ef["y"]-100))
        elif ef["type"] == "laser_beam":
            alpha = int(255 * (1 - elapsed/ef["dur"]))
            pygame.draw.line(screen, (0,255,255,alpha), (ef["x"], ef["y"]-20), (WIDTH, ef["y"]), 6)
            pygame.draw.line(screen, (100,255,255,alpha), (ef["x"], ef["y"]-20), (WIDTH, ef["y"]), 3)
        elif ef["type"] == "lightning":
            alpha = int(255 * (1 - elapsed/ef["dur"]))
            points = [(ef["x1"], ef["y1"])]
            for _ in range(5):
                mx = (ef["x1"] + ef["x2"]) / 2 + random.randint(-30,30)
                my = (ef["y1"] + ef["y2"]) / 2 + random.randint(-30,30)
                points.append((mx, my))
            points.append((ef["x2"], ef["y2"]))
            pygame.draw.lines(screen, (200,200,255,alpha), False, points, 4)
            pygame.draw.lines(screen, (255,255,100,alpha), False, points, 2)
        elif ef["type"] == "laser_warning":
            alpha = int(255 * (1 - elapsed/ef["dur"]))
            pygame.draw.line(screen, (255,0,0,alpha), (0, ef["y"]), (WIDTH, ef["y"]), 8)
            pygame.draw.line(screen, (255,100,100,alpha), (0, ef["y"]-4), (WIDTH, ef["y"]+4), 4)
        elif ef["type"] == "hit_flash" and boss:
            alpha = int(255 * (1 - elapsed/ef["dur"]))
            overlay = pygame.Surface((200, 200), pygame.SRCALPHA)
            overlay.fill((255, 200, 100, alpha))
            screen.blit(overlay, (boss["x"]-100, boss["y"]-100))
        else:
            img = ef.get("img")
            if img:
                alpha = int(255 * (1 - elapsed/ef["dur"]))
                img.set_alpha(alpha)
                screen.blit(img, (int(ef["x"]-img.get_width()//2)+shake_offset[0], int(ef["y"]-img.get_height()//2)+shake_offset[1]))

    for fp in float_pops[:]:
        t = now() - fp["t"]
        if t > fp["dur"]:
            float_pops.remove(fp)
            continue
        surf = font.render(fp["txt"], True, fp.get("color",(255,255,150)))
        screen.blit(surf, (int(fp["x"] - surf.get_width()//2) + shake_offset[0],
                           int(fp["y"] - t*50) + shake_offset[1]))

    # UI - display score/level/hp like before, plus new Speed/Damage levels and Shield bar
    level_color = (255,215,0) if player["level"] >= TRANSFORM_LEVEL else (255,255,255)
    screen.blit(font.render(f"SCORE: {score}", True, (255,255,255)), (12,10))
    screen.blit(font.render(f"LVL: {player['level']}/{MAX_LEVEL}", True, level_color), (12,34))
    screen.blit(font.render(f"HP: {player['hp']}", True, (255,100,100)), (12,58))

    # Speed & Damage levels (cap 10)
    sp_lvl = player.get("speed_level", 1)
    dmg_lvl = player.get("damage_level", 1)
    screen.blit(font.render(f"SPEED LVL: {sp_lvl}/10", True, (200,200,255)), (12,82))
    screen.blit(font.render(f"DAMAGE LVL: {dmg_lvl}/10", True, (200,200,255)), (12,104))

    sub_text = sub_weapon.upper()
    color = (255,100,100) if sub_weapon == "missile" else (0,255,255) if sub_weapon == "laser" else (200,200,255)
    screen.blit(font.render(f"SUB: {sub_text}", True, color), (12, 128))
    screen.blit(sub_imgs[sub_weapon], (90, 124))
    if sub_cooldown > 0:
        bar_w = 80
        ratio = sub_cooldown / SUB_COOLDOWN_TIME
        pygame.draw.rect(screen, (60,60,60), (12, 152, bar_w, 6))
        pygame.draw.rect(screen, color, (12, 152, bar_w * (1 - ratio), 6))

    # Shield HUD
    shield = player.get("shield", 0)
    shield_max = player.get("shield_max", 30)
    sx, sy = 12, 170
    pygame.draw.rect(screen, (30,30,30), (sx, sy, 140, 12))
    if shield_max > 0:
        pygame.draw.rect(screen, (100,200,255), (sx, sy, int(140 * (shield / shield_max)), 12))
    screen.blit(font.render(f"SHIELD: {int(shield)}/{int(shield_max)}", True, (100,220,255)), (sx + 148, sy - 2))

    helper_text = font.render(f"DINO: {helper_count}", True, (100,255,100))
    screen.blit(helper_text, (12, 196))
    if helpers:
        screen.blit(dino_img, (90, 192))
    if boss:
        boss_name = {"normal": "BOSS 1", "smart": "BOSS 2", "apocalypse": "BOSS 3", "nexus": "NEXUS BOSS"}.get(boss.get("type", "normal"), "BOSS")
        color = (255,0,0) if "NEXUS" not in boss_name else (255,50,255)
        screen.blit(bigfont.render(boss_name, True, color), (WIDTH//2 - 80, 20))

    bomb_x, bomb_y = WIDTH - 100, HEIGHT - 70
    if bomb_cooldown <= 0:
        pulse = 1.0 + 0.1 * sin(now() * 8)
        frame = bomb_frames[bomb_anim_index]
        scaled = pygame.transform.smoothscale(frame, (int(60*pulse), int(60*pulse)))
        screen.blit(scaled, (bomb_x - scaled.get_width()//2, bomb_y - scaled.get_height()//2))
        screen.blit(font.render("READY", True, (100,255,100)), (bomb_x - 50, bomb_y + 40))
    else:
        frame = bomb_frames[bomb_anim_index]
        screen.blit(frame, (bomb_x - 30, bomb_y - 30))
        ratio = bomb_cooldown / BOMB_COOLDOWN_TIME
        pygame.draw.circle(screen, (60,60,60), (bomb_x, bomb_y), 35, 5)
        pygame.draw.arc(screen, (255,100,100), (bomb_x-35, bomb_y-35, 70, 70),
                        math.pi/2, math.pi/2 + 2*math.pi*(1-ratio), 5)
        txt = font.render(f"{int(bomb_cooldown)}s", True, (255,100,100))
        screen.blit(txt, (bomb_x - txt.get_width()//2, bomb_y - 10))

def load_transform_frames(base_name="assets/hero_transform", canvas=HERO_CANVAS):
    """
    Load hero_transform1..3 and ensure each frame is centered on HERO_CANVAS.
    If a frame is smaller than canvas, scale it up (preserving aspect) so it visually matches the normal hero size.
    If none are found, fall back to hero_transform_img (also normalized to canvas).
    """
    frames = []
    for i in range(1, 4):
        path = f"{base_name}{i}.png"
        img = load_image_safe(path)
        # load_image_safe returns placeholder surface on missing files; check width
        if not hasattr(img, "get_width") or img.get_width() <= 8:
            continue
        iw, ih = img.get_size()
        cw, ch = canvas
        # scale image to best-fit canvas while preserving aspect ratio (scale up or down)
        scale = min(cw / max(1, iw), ch / max(1, ih))
        if abs(scale - 1.0) > 0.001:
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            try:
                img = pygame.transform.smoothscale(img, (new_w, new_h))
            except Exception:
                img = pygame.transform.scale(img, (new_w, new_h))
        # center on canvas
        tmp = pygame.Surface(canvas, pygame.SRCALPHA)
        tx = (cw - img.get_width()) // 2
        ty = (ch - img.get_height()) // 2
        tmp.blit(img, (tx, ty))
        frames.append(tmp)
    if not frames:
        # fallback - use pre-existing hero_transform_img if present (ensure it's canvas-sized)
        try:
            base = hero_transform_img
            if base.get_size() != canvas:
                iw, ih = base.get_size()
                cw, ch = canvas
                scale = min(cw / max(1, iw), ch / max(1, ih))
                new_w = max(1, int(iw * scale))
                new_h = max(1, int(ih * scale))
                try:
                    base_s = pygame.transform.smoothscale(base, (new_w, new_h))
                except Exception:
                    base_s = pygame.transform.scale(base, (new_w, new_h))
                tmp = pygame.Surface(canvas, pygame.SRCALPHA)
                tx = (cw - new_w) // 2
                ty = (ch - new_h) // 2
                tmp.blit(base_s, (tx, ty))
                frames = [tmp]
            else:
                frames = [base.copy()]
        except Exception:
            frames = []
    # Debug (one-time print to help troubleshooting)
    try:
        sizes = [f.get_size() for f in frames]
        print("loaded transform frames:", len(frames), "sizes:", sizes)
    except Exception:
        pass
    return frames

def slice_atlas_by_alpha(path):
    """
    Loads an atlas image and returns a list of subsurfaces (copied) for each connected non-transparent region.
    Accepts either a relative asset path (e.g. "assets/transform_bullets.png") or an absolute path.
    Also normalizes each sliced sprite to a reasonable maximum size to avoid extremely large blobs.
    """
    # load the surface robustly regardless of whether caller passed ap(...) or a relative path
    surf = None
    try:
        if os.path.isabs(path) and os.path.exists(path):
            surf = pygame.image.load(path).convert_alpha()
        else:
            # treat as project-relative name
            surf = load_image_safe(path)
    except Exception:
        try:
            # fallback: try load_image_safe on absolute path too
            surf = load_image_safe(path)
        except Exception:
            surf = None

    if not surf or getattr(surf, "get_width", lambda: 0)() < 8:
        return []

    rects = _find_connected_components_alpha(surf)
    frames = []
    MAX_DIM = 48  # scale down very large projectile slices to this maximum dimension
    for r in rects:
        try:
            sub = surf.subsurface(r).copy()
            sw, sh = sub.get_size()
            if max(sw, sh) > MAX_DIM:
                s = MAX_DIM / max(sw, sh)
                new_w = max(1, int(sw * s))
                new_h = max(1, int(sh * s))
                try:
                    sub = pygame.transform.smoothscale(sub, (new_w, new_h))
                except Exception:
                    sub = pygame.transform.scale(sub, (new_w, new_h))
            frames.append(sub)
        except Exception:
            continue
    # If slicing produced no small pieces but the atlas itself is usable, return scaled atlas as single sprite
    if not frames:
        sw, sh = surf.get_size()
        if max(sw, sh) > 0:
            if max(sw, sh) > MAX_DIM:
                s = MAX_DIM / max(sw, sh)
                try:
                    surf_small = pygame.transform.smoothscale(surf, (max(1, int(sw * s)), max(1, int(sh * s))))
                except Exception:
                    surf_small = pygame.transform.scale(surf, (max(1, int(sw * s)), max(1, int(sh * s))))
                frames = [surf_small]
            else:
                frames = [surf.copy()]
    # Debug info
    try:
        sizes = [f.get_size() for f in frames]
        print("sliced atlas into", len(frames), "frames sizes:", sizes)
    except Exception:
        pass
    return frames

def load_transform_and_bullets():
    """
    Convenience loader that returns (transform_frames, transform_bullet_frames).
    Uses relative paths (not ap()) so load_image_safe works consistently.
    """
    t_frames = load_transform_frames(base_name="assets/hero_transform", canvas=HERO_CANVAS)
    # pass relative path to the slicer so it uses load_image_safe internally
    b_frames = slice_atlas_by_alpha("assets/transform_bullets.png")
    # If slicing produced nothing, attempt a fallback using load_image_safe and scale it small
    if not b_frames:
        surf = load_image_safe("assets/transform_bullets.png")
        if hasattr(surf, "get_width") and surf.get_width() > 8:
            sw, sh = surf.get_size()
            MAX_DIM = 48
            if max(sw, sh) > MAX_DIM:
                s = MAX_DIM / max(sw, sh)
                try:
                    surf_small = pygame.transform.smoothscale(surf, (max(1, int(sw * s)), max(1, int(sh * s))))
                except Exception:
                    surf_small = pygame.transform.scale(surf, (max(1, int(sw * s)), max(1, int(sh * s))))
                b_frames = [surf_small]
            else:
                b_frames = [surf]
    # Final debug
    try:
        print("transform_frames:", len(t_frames), "transform_bullets:", len(b_frames))
    except Exception:
        pass
    return t_frames, b_frames

def slice_atlas_by_alpha(path):
    """
    Loads an atlas image and returns a list of subsurfaces (copied) for each connected non-transparent region.
    If the atlas is missing or empty, returns an empty list.
    """
    surf = load_image_safe(path)
    if not surf or getattr(surf, "get_width", lambda:0)() < 8:
        return []
    rects = _find_connected_components_alpha(surf)
    frames = []
    for r in rects:
        try:
            sub = surf.subsurface(r).copy()
            # trim transparent border a little further if needed (optional)
            frames.append(sub)
        except Exception:
            continue
    return frames

def load_transform_and_bullets():
    """
    Convenience loader that returns (transform_frames, transform_bullet_frames).
    Call once after assets are available (e.g. after calling install_dino_chain).
    """
    t_frames = load_transform_frames(base_name="assets/hero_transform", canvas=HERO_CANVAS)
    b_frames = slice_atlas_by_alpha(ap("assets/transform_bullets.png"))
    # If slicing produced no frames, attempt to use single large image as one bullet
    if not b_frames and hasattr(surf := load_image_safe("assets/transform_bullets.png"), "get_width"):
        if surf.get_width() > 8:
            b_frames = [surf]
    return t_frames, b_frames

# Example usage (call this once after loader definitions in your main file):
try:
    transform_frames, transform_bullet_imgs = load_transform_and_bullets()
except Exception:
    transform_frames = [hero_transform_img] if 'hero_transform_img' in globals() else []
    transform_bullet_imgs = []

def draw_scene_title():
    global scroll_x
    if stage_img:
        w = stage_img.get_width()
        scroll_x = (scroll_x + scroll_speed * 0.5) % w
        x = -int(scroll_x)
        while x < WIDTH:
            screen.blit(stage_img, (x, 0))
            x += w
    else:
        screen.fill((8,12,28))
    title_surf = bigfont.render("SKY RUINS", True, (255,215,0))
    glow_surf = bigfont.render("SKY RUINS", True, (255,100,0))
    pulse = 1.0 + 0.1 * sin(now() * 4)
    gw, gh = int(glow_surf.get_width() * pulse), int(glow_surf.get_height() * pulse)
    glow_scaled = pygame.transform.smoothscale(glow_surf, (gw, gh))
    glow_scaled.set_alpha(80)
    screen.blit(glow_scaled, (WIDTH//2 - gw//2, 120))
    screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 120))
    subtitle = font.render("PRESS X TO CYCLE SUB-WEAPON • B FOR BOMB • ENTER TO PLAY", True, (200,200,255))
    screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 220))
    controls = [
        font.render("ARROW KEYS / WASD: MOVE", True, (150,200,255)),
        font.render("SPACE: SHOOT + SUB (3s CD)", True, (150,200,255)),
        font.render("X: CYCLE SUB-WEAPON", True, (150,200,255)),
        font.render("B: BOMB (20s CD)", True, (150,200,255))
    ]
    for i, ctrl in enumerate(controls):
        screen.blit(ctrl, (WIDTH//2 - ctrl.get_width()//2, 280 + i*25))
import math
import pygame

# Config — tweak to taste
WING_FRAME_COUNT = 6           # number of animation frames for flap cycle
WING_ANIM_INTERVAL = 0.06      # seconds per wing frame
WING_BASE_WIDTH = int(HERO_CANVAS[0] * 0.9)   # visual width of wings
WING_BASE_HEIGHT = int(HERO_CANVAS[1] * 0.55) # visual height of wings
WING_COLOR = (120, 200, 255)   # base plasma color
WING_GLOW = (140, 220, 255)    # glow color

# Runtime animation state
wing_frames_left = []   # list of Surfaces for left wing (animated)
wing_frames_right = []  # mirrored copies for right wing
wing_anim_index = 0
wing_a    nim_timer = 0.0

def _draw_plasma_layer(surf, cx, cy, w, h, phase, color, alpha):
    """
    Draws a single plasma "feather" layer onto surf using multiple ellipses/polys modulated by phase.
    """
    col = (*color, int(alpha))
    for i in range(6):
        t = i / 6.0
        rx = int(w * (0.25 + 0.7 * (1 - t)))
        ry = int(h * (0.18 + 0.6 * (1 - t)))
        ox = int((math.sin(phase * (1 + t*1.2) + i) * rx * 0.15) )
        oy = int((math.cos(phase * 1.3 + i*1.1) * ry * 0.06))
        rect = pygame.Rect(0, 0, rx*2, ry*2)
        rect.center = (cx + int((t-0.2)*w*0.6) + ox, cy + int(t*h*0.6) + oy)
        pygame.draw.ellipse(surf, col, rect)

def _create_single_wing_frame(w, h, flap_amount, base_color=WING_COLOR, glow_color=WING_GLOW):
    """
    Create one wing surface (left-oriented). flap_amount should be in [-1..1].
    """
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    cy = h // 3
    # base glow: multiple semi-transparent blurred-ish ellipses
    for g in range(3):
        alpha = 60 - g*18
        scale = 1.0 + g*0.12
        _draw_plasma_layer(surf, cx, cy, int(w*scale), int(h*scale), flap_amount*3.0 + g, glow_color, alpha)
    # core feathers: brighter, tighter
    _draw_plasma_layer(surf, cx, cy - int(h*0.06), int(w*0.95), int(h*0.9), flap_amount*4.0, base_color, 160)
    # add a few highlight strokes
    for i in range(3):
        px = int(cx + (i-1)*w*0.12 + math.sin(flap_amount*2.0 + i)*6)
        py = int(cy + i*h*0.18 + math.cos(flap_amount*1.5 + i)*4)
        pygame.draw.line(surf, (*glow_color, 200), (px-6, py), (px+int(w*0.25), py - int(h*0.08)), 3)
    return surf

def create_plasma_wing_frames(frame_count=WING_FRAME_COUNT, size=(WING_BASE_WIDTH, WING_BASE_HEIGHT)):
    """
    Returns (left_frames, right_frames) lists of surfaces.
    Each frame is left-oriented; right frames are mirrored.
    """
    left = []
    right = []
    w, h = size
    for i in range(frame_count):
        # flap phase between -1 and 1
        phase = math.sin((i / frame_count) * math.pi * 2.0)
        flap = phase
        f = _create_single_wing_frame(w, h, flap)
        left.append(f)
        # create mirrored right wing
        right.append(pygame.transform.flip(f, True, False))
    return left, right

# Integration helpers — call once after pygame/init and HERO_CANVAS available
def init_plasma_wings():
    global wing_frames_left, wing_frames_right, wing_anim_index, wing_anim_timer
    try:
        left, right = create_plasma_wing_frames(WING_FRAME_COUNT, (WING_BASE_WIDTH, WING_BASE_HEIGHT))
        wing_frames_left = left
        wing_frames_right = right
        wing_anim_index = 0
        wing_anim_timer = now()
        # debug:
        print("plasma wings loaded:", len(wing_frames_left), "frames; frame size:", wing_frames_left[0].get_size() if wing_frames_left else None)
    except Exception as e:
        print("init_plasma_wings failed:", e)
        wing_frames_left = []
        wing_frames_right = []

# Call init_plasma_wings() after assets are loaded (example below in integration notes)

def draw_scene_game_over():
    screen.fill((40,0,0))
    pulse = 0.3 + 0.2 * sin(now() * 3)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((255,0,0,int(80*pulse)))
    screen.blit(overlay, (0,0))
    go_surf = bigfont.render("GAME OVER", True, (255,50,50))
    glow = bigfont.render("GAME OVER", True, (255,0,0))
    pulse = 1.0 + 0.1 * sin(now() * 4)
    gw, gh = int(glow.get_width() * pulse), int(glow.get_height() * pulse)
    glow_scaled = pygame.transform.smoothscale(glow, (gw, gh))
    glow_scaled.set_alpha(100)
    screen.blit(glow_scaled, (WIDTH//2 - gw//2, 100))
    screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, 100))
    score_surf = font.render(f"FINAL SCORE: {score}", True, (255,255,100))
    screen.blit(score_surf, (WIDTH//2 - score_surf.get_width()//2, 180))
    new_high = score > high_score
    hs_color = (255,215,0) if new_high else (200,200,200)
    hs_surf = font.render(f"HIGH SCORE: {max(score, high_score)}", True, hs_color)
    screen.blit(hs_surf, (WIDTH//2 - hs_surf.get_width()//2, 210))
    restart_surf = font.render("PRESS ENTER TO RESTART", True, (200,200,255))
    screen.blit(restart_surf, (WIDTH//2 - restart_surf.get_width()//2, 280))
    ctrl = font.render("ESC = QUIT", True, (150,150,150))
    screen.blit(ctrl, (WIDTH//2 - ctrl.get_width()//2, 320))

# ---------------- MAIN LOOP ----------------
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            if scene == "title" and ev.key == pygame.K_RETURN:
                scene = "game"
                player.update({"hp":100, "level":1, "exp":0, "transformed":False, "shield": 0, "shield_max": 30, "speed_level": 1, "damage_level": 1})
                score = 0
                bullets.clear(); enemies.clear(); powerups.clear(); boss = None; particles.clear()
                helpers.clear(); helper_count = 0; helper_spawn_timer = now()
                enemy_spawn_timer = time.time()
                bomb_cooldown = 0
                sub_cooldown = 0
                # reset transform visuals
                transform_anim_index = 0
                transform_anim_timer = now()
                transform_draw_offset = 0.0
                transform_fly_phase = 0.0
                transform_thrust_timer = now()
                if os.path.exists(music_path):
                    pygame.mixer.music.play(-1)
            if scene == "game_over" and ev.key == pygame.K_RETURN:
                scene = "game"
                player.update({"hp":100, "level":1, "exp":0, "transformed":False, "shield": 0, "shield_max": 30, "speed_level": 1, "damage_level": 1})
                score = 0
                bullets.clear(); enemies.clear(); powerups.clear(); boss = None; particles.clear()
                helpers.clear(); helper_count = 0; helper_spawn_timer = now()
                enemy_spawn_timer = time.time()
                bomb_cooldown = 0
                sub_cooldown = 0
                transform_anim_index = 0
                transform_anim_timer = now()
                transform_draw_offset = 0.0
                transform_fly_phase = 0.0
                transform_thrust_timer = now()
                if os.path.exists(music_path):
                    pygame.mixer.music.play(-1)
            if scene == "game" and ev.key == pygame.K_SPACE:
                player_shoot()
                if sub_cooldown <= 0:
                    player_sub_shoot()
            if scene == "game" and ev.key == pygame.K_b:
                activate_bomb()
            if scene == "game" and ev.key == pygame.K_x:
                sub_cycle_index = (sub_cycle_index + 1) % len(sub_weapons)
                sub_weapon = sub_weapons[sub_cycle_index]
                color = (255,100,100) if sub_weapon == "missile" else (0,255,255) if sub_weapon == "laser" else (200,200,255)
                add_float_pop(WIDTH//2, HEIGHT//2 - 50, f"{sub_weapon.upper()} READY!", color)

    keys = pygame.key.get_pressed()
    if scene == "game":
        dx = dy = 0
        # effective movement speed considers speed_level (capped at 10)
        speed_level = clamp(player.get("speed_level",1), 1, 10)
        base_speed = PLAYER_SPEED * (1.0 + 0.08 * (speed_level - 1))
        if player.get("transformed", False):
            effective_speed = base_speed * TRANSFORM_MOVE_BOOST
        else:
            effective_speed = base_speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= effective_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += effective_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= effective_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += effective_speed
        if dx and dy: dx *= 0.7071; dy *= 0.7071
        player["x"] = clamp(player["x"] + dx, 40, WIDTH-40)
        player["y"] = clamp(player["y"] + dy, 40, HEIGHT-40)

        # transform flight visuals: bobbing + thruster particles (visual only)
        if player.get("transformed", False):
            transform_fly_phase += dt * TRANSFORM_FLY_SPEED
            transform_draw_offset = math.sin(transform_fly_phase) * TRANSFORM_FLY_AMPLITUDE
            if now() - transform_thrust_timer > TRANSFORM_THRUST_PART_INTERVAL:
                transform_thrust_timer = now()
                # left thruster
                create_particles(player["x"] - 10, player["y"] + 22, count=3, color=(255,180,80),
                                 speed=2.4, life=0.35, size=3, gravity=0.08, spread=40)
                # right thruster
                create_particles(player["x"] + 10, player["y"] + 22, count=3, color=(255,180,80),
                                 speed=2.4, life=0.35, size=3, gravity=0.08, spread=40)
        else:
            transform_draw_offset = 0.0

        if keys[pygame.K_SPACE]:
            player_shoot()
            if sub_cooldown <= 0:
                player_sub_shoot()

        # DINO HELPER MIMIC
        for h in helpers:
            if keys[pygame.K_SPACE] and now() - h["last_mimic"] > h["mimic_delay"]:
                row = selected_hero
                shots = 1 + (player["level"] >= 10)
                for i in range(shots):
                    angle = radians(-10 + 20*i) if shots > 1 else 0
                    vx = BULLET_SPEED * 0.9 * cos(angle)
                    vy = BULLET_SPEED * 0.9 * sin(angle)
                    # helper bullets incorporate player's damage_level
                    base_damage = max(1, player.get("damage_level",1))
                    bullets.append({
                        "x": h["x"] + 24, "y": h["y"], "vx": vx, "vy": vy,
                        "img": bullet_imgs[row], "glow": True,
                        "damage": base_damage
                    })
                effects.append({
                    "type": "muzzle", "x": h["x"]+30, "y": h["y"],
                    "img": muzzle_imgs[row], "t": now(), "dur": 0.1, "glow": True
                })
                h["last_mimic"] = now()
                if shoot_sound: shoot_sound.play()
            if sub_cooldown <= 0 and keys[pygame.K_SPACE] and now() - h["last_mimic"] > 0.25:
                if sub_weapon == "missile":
                    bullets.append({
                        "x": h["x"]+28, "y": h["y"], "vx": 28, "vy": 0,
                        "img": sub_imgs["missile"], "glow": True, "damage": 12,
                        "type": "missile", "homing": True, "target": None
                    })
                    create_particles(h["x"]+32, h["y"], 6, (255,150,50), 8, 0.4)
                elif sub_weapon == "laser":
                    bullets.append({
                        "x": h["x"]+28, "y": h["y"], "vx": 85, "vy": 0,
                        "img": sub_imgs["laser"], "glow": True, "damage": 6,
                        "type": "laser", "pierce": 99
                    })
                    effects.append({"type": "laser_beam", "x": h["x"]+28, "y": h["y"], "t": now(), "dur": 0.25})
                elif sub_weapon == "lightning":
                    targets = enemies[:]
                    if boss: targets.append(boss)
                    if targets:
                        start = {"x": h["x"]+28, "y": h["y"]}
                        chain_all_lightning(start, targets, 14)
                h["last_mimic"] = now()

        update_entities(dt)

        # apply shake
        if now() - shake_timer < 0.4:
            intensity = 12 if now() - shake_timer < 0.2 else 6
            shake_offset = (random.randint(-intensity, intensity), random.randint(-intensity, intensity))
        else:
            shake_offset = (0,0)

        if player["hp"] <= 0:
            if score > high_score:
                with open(HIGH_SCORE_FILE, "w") as f:
                    f.write(str(score))
                high_score = score
            for _ in range(30):
                create_particles(player["x"], player["y"], 20, (255,100,0), 15, 1.5, 5, 0.8)
            scene = "game_over"

    # SMOOTH DINO HELPER FOLLOW (CHAINED)
    # Use dino_chain_update if installed; otherwise fall back to original lerp follow.
    if 'dino_chain_update' in globals():
        try:
            dino_chain_update(player, helpers)
        except Exception:
            # fallback to original per-helper offsets lerp
            for h in helpers:
                target_x = player["x"] + h.get("offset_x", -60)
                target_y = player["y"] + h.get("offset_y", 0)
                lerp_speed = 0.06
                h["x"] += (target_x - h["x"]) * lerp_speed
                h["y"] += (target_y - h["y"]) * lerp_speed
    else:
        for h in helpers:
            target_x = player["x"] + h["offset_x"]
            target_y = player["y"] + h["offset_y"]
            lerp_speed = 0.04
            h["x"] += (target_x - h["x"]) * lerp_speed
            h["y"] += (target_y - h["y"]) * lerp_speed

    if scene == "title":
        draw_scene_title()
    elif scene == "game":
        draw_scene_game()
    elif scene == "game_over":
        draw_scene_game_over()

    pygame.display.flip()

pygame.quit()
sys.exit()
