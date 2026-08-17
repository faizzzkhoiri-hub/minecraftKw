import pygame
import math
import random
import json
import os
import sys
import time
from enum import IntEnum

pygame.init()

try:
    pygame.mixer.init()
except Exception:
    pass


# =========================================================
# DISPLAY
# =========================================================

W, H = (
    pygame.display.Info().current_w or 1280,
    pygame.display.Info().current_h or 720
)

screen = pygame.display.set_mode(
    (W, H),
    pygame.FULLSCREEN | pygame.SCALED
)

pygame.display.set_caption("minecraftKw v1")

clock = pygame.time.Clock()

font = pygame.font.Font(
    None,
    max(22, H // 32)
)

small = pygame.font.Font(
    None,
    max(18, H // 42)
)

big = pygame.font.Font(
    None,
    max(34, H // 20)
)


# =========================================================
# BLOCKS
# =========================================================

class B(IntEnum):
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3
    WOOD = 4
    LEAVES = 5
    SAND = 6
    GRAVEL = 7
    COBBLE = 8
    LOG = 9
    WATER = 10
    LAVA = 11
    COAL = 12
    IRON = 13
    GLASS = 14
    PLANK = 15


COL = {
    B.GRASS: (74, 170, 68),
    B.DIRT: (130, 82, 45),
    B.STONE: (120, 120, 125),
    B.WOOD: (125, 78, 38),
    B.LEAVES: (50, 145, 60),
    B.SAND: (220, 200, 145),
    B.GRAVEL: (145, 145, 140),
    B.COBBLE: (95, 95, 95),
    B.LOG: (110, 68, 35),
    B.WATER: (45, 125, 205),
    B.LAVA: (235, 90, 20),
    B.COAL: (45, 45, 45),
    B.IRON: (180, 145, 115),
    B.GLASS: (180, 225, 240),
    B.PLANK: (190, 130, 70),
}

NAME = {
    b: b.name.title()
    for b in B
}

SOLID = {
    b: True
    for b in B
}

SOLID.update({
    B.AIR: False,
    B.WATER: False,
    B.LAVA: False,
})

HARD = {
    B.GRASS: 1,
    B.DIRT: 1,
    B.STONE: 3,
    B.WOOD: 2,
    B.LEAVES: 1,
    B.SAND: 1,
    B.GRAVEL: 1,
    B.COBBLE: 4,
    B.LOG: 2,
    B.COAL: 4,
    B.IRON: 5,
    B.GLASS: 1,
    B.PLANK: 2,
}

DROP = {
    B.GRASS: B.DIRT,
    B.STONE: B.COBBLE,
    B.LOG: B.WOOD,
    B.COAL: B.COAL,
    B.IRON: B.IRON,
    B.GLASS: B.GLASS,
    B.PLANK: B.PLANK,
}

HOT = [
    B.DIRT,
    B.WOOD,
    B.COBBLE,
    B.STONE,
    B.SAND,
    B.LOG,
    B.PLANK,
    B.GLASS,
    B.COAL,
]

RECIPES = [
    (
        "Planks",
        {B.WOOD: 1},
        {B.PLANK: 4}
    ),
    (
        "Stick",
        {B.PLANK: 2},
        {"stick": 4}
    ),
    (
        "Wood Pick",
        {B.PLANK: 3, "stick": 2},
        {"tool": "wood_pick"}
    ),
    (
        "Stone Pick",
        {B.COBBLE: 3, "stick": 2},
        {"tool": "stone_pick"}
    ),
    (
        "Iron Pick",
        {B.IRON: 3, "stick": 2},
        {"tool": "iron_pick"}
    ),
    (
        "Glass",
        {B.SAND: 1},
        {B.GLASS: 1}
    ),
]


# =========================================================
# SAVE
# =========================================================

SAVE_DIR = "saves"

try:
    os.makedirs(SAVE_DIR, exist_ok=True)
except Exception:
    pass


# =========================================================
# WORLD
# =========================================================

class World:

    def __init__(self, seed=None):
        self.seed = seed or random.randrange(1, 2 ** 31)
        self.blocks = {}
        self.mobs = []
        self.time = 0
        self.generated = set()

    def noise(self, x, z):
        r = random.Random(
            (
                self.seed * 73856093
                + x * 19349663
                + z * 83492791
            ) & 0xffffffff
        )
        return r.random()

    def gen_chunk(self, cx, cz):

        if (cx, cz) in self.generated:
            return

        self.generated.add((cx, cz))

        random.seed(
            self.seed
            + cx * 991
            + cz * 313
        )

        for x in range(cx * 12, cx * 12 + 12):

            for z in range(cz * 12, cz * 12 + 12):

                n = (
                    math.sin(x * 0.09)
                    + math.cos(z * 0.08)
                    + math.sin((x + z) * 0.035)
                ) * 0.5

                h = max(
                    2,
                    min(
                        22,
                        9 + int(
                            n * 5
                            + self.noise(
                                x // 3,
                                z // 3
                            ) * 2
                        )
                    )
                )

                beach = h <= 6

                for y in range(h):

                    if y < h - 4:
                        block = B.STONE
                    elif beach:
                        block = B.SAND
                    else:
                        block = B.DIRT

                    self.blocks[(x, y, z)] = block

                self.blocks[
                    (x, h, z)
                ] = B.SAND if beach else B.GRASS

                # TREE
                if h > 7 and random.random() < 0.035:

                    for y in range(h + 1, h + 5):
                        self.blocks[
                            (x, y, z)
                        ] = B.LOG

                    for dx in range(-2, 3):
                        for dz in range(-2, 3):

                            if dx * dx + dz * dz < 7:

                                self.blocks[
                                    (
                                        x + dx,
                                        h + 5,
                                        z + dz
                                    )
                                ] = B.LEAVES

                # ORE
                if random.random() < 0.06:

                    oy = random.randint(
                        2,
                        max(2, h - 4)
                    )

                    if random.random() < 0.6:
                        ore = B.COAL
                    else:
                        ore = B.IRON

                    self.blocks[
                        (x, oy, z)
                    ] = ore

                # WATER
                if beach and random.random() < 0.025:

                    self.blocks[
                        (x, h, z)
                    ] = B.WATER

    def ensure(self, x, z, r=1):

        cx = math.floor(x / 12)
        cz = math.floor(z / 12)

        for a in range(cx - r, cx + r + 1):

            for b in range(cz - r, cz + r + 1):

                self.gen_chunk(a, b)

    def get(self, x, y, z):

        if y < 0:
            return B.STONE

        return self.blocks.get(
            (
                int(x),
                int(y),
                int(z)
            ),
            B.AIR
        )

    def set(self, x, y, z, b):

        if 0 <= y < 128:

            self.blocks[
                (
                    int(x),
                    int(y),
                    int(z)
                )
            ] = b

    def surface(self, x, z):

        for y in range(127, 0, -1):

            if SOLID.get(
                self.get(x, y, z),
                False
            ):
                return y + 1

        return 10

    def save(self, p, slot="world.json"):

        try:

            data = {
                "seed": self.seed,
                "time": self.time,
                "player": p.pack(),
                "blocks": [
                    [
                        x,
                        y,
                        z,
                        b.value
                    ]
                    for (x, y, z), b
                    in self.blocks.items()
                ]
            }

            with open(
                os.path.join(
                    SAVE_DIR,
                    slot
                ),
                "w"
            ) as f:

                json.dump(
                    data,
                    f
                )

            return True

        except Exception:
            return False

    def load(self, p, slot="world.json"):

        path = os.path.join(
            SAVE_DIR,
            slot
        )

        if not os.path.exists(path):
            return False

        try:

            with open(path) as f:
                d = json.load(f)

            self.seed = d["seed"]
            self.time = d.get(
                "time",
                0
            )

            self.blocks = {
                (
                    a,
                    b,
                    c
                ): B(v)

                for a, b, c, v
                in d.get(
                    "blocks",
                    []
                )
            }

            self.generated = set()

            p.unpack(
                d.get(
                    "player",
                    {}
                )
            )

            return True

        except Exception:
            return False


# =========================================================
# PLAYER
# =========================================================

class Player:

    def __init__(self, w):

        self.x = 0.5
        self.z = 0.5
        self.y = w.surface(0, 0)

        self.yaw = 0
        self.pitch = 0

        self.vy = 0
        self.ground = False

        self.hp = 20
        self.food = 20
        self.sat = 5

        self.inv = {
            B.DIRT: 16,
            B.WOOD: 4,
            B.COBBLE: 8,
            B.STONE: 4
        }

        self.tools = {
            "hand": 999,
            "wood_pick": 60,
            "stone_pick": 132,
            "iron_pick": 251
        }

        self.tool = "hand"
        self.sel = 0

        self.breaking = None
        self.progress = 0

        self.attack_cd = 0

    def pack(self):

        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "hp": self.hp,
            "food": self.food,
            "inv": {
                str(int(k)): v
                for k, v in self.inv.items()
                if isinstance(k, B)
            },
            "tools": self.tools,
            "tool": self.tool,
            "sel": self.sel
        }

    def unpack(self, d):

        for k in (
            "x",
            "y",
            "z",
            "yaw",
            "pitch",
            "hp",
            "food"
        ):

            if k in d:
                setattr(
                    self,
                    k,
                    d[k]
                )

        self.inv = {
            B(int(k)): v
            for k, v in d.get(
                "inv",
                {}
            ).items()
        }

        self.tools = d.get(
            "tools",
            self.tools
        )

        self.tool = d.get(
            "tool",
            "hand"
        )

        self.sel = d.get(
            "sel",
            0
        )

    def solid_at(self, w, x, y, z):

        return SOLID.get(
            w.get(
                math.floor(x),
                math.floor(y),
                math.floor(z)
            ),
            False
        )

    def move(self, w, dx, dz):

        nx = self.x + dx
        nz = self.z + dz

        blocked = any(
            self.solid_at(
                w,
                nx + sx,
                self.y,
                nz + sz
            )

            for sx in (-0.28, 0.28)
            for sz in (-0.28, 0.28)
        )

        if not blocked:
            self.x = nx
            self.z = nz

    def update(
        self,
        w,
        dt,
        keys,
        touch_controls=None
    ):

        w.ensure(
            self.x,
            self.z,
            2
        )

        speed = 4.2 * dt

        # KEYBOARD
        f = (
            int(keys[pygame.K_w])
            - int(keys[pygame.K_s])
        )

        s = (
            int(keys[pygame.K_d])
            - int(keys[pygame.K_a])
        )

        # TOUCH
        if touch_controls:

            if touch_controls.get("left"):
                s -= 1

            if touch_controls.get("right"):
                s += 1

            if touch_controls.get("up"):
                f += 1

            if touch_controls.get("down"):
                f -= 1

        ln = math.hypot(f, s)

        if ln == 0:
            ln = 1

        sy = math.sin(self.yaw)
        cy = math.cos(self.yaw)

        self.move(
            w,
            (
                sy * f
                + cy * s
            ) / ln * speed,

            (
                -cy * f
                + sy * s
            ) / ln * speed
        )

        # GRAVITY
        self.vy -= 18 * dt

        ny = self.y + self.vy * dt

        if (
            self.vy < 0
            and self.solid_at(
                w,
                self.x,
                ny - 0.9,
                self.z
            )
        ):

            self.y = (
                math.floor(ny) + 1
            )

            self.vy = 0
            self.ground = True

        else:

            self.y = ny
            self.ground = False

        if self.y < 0:
            self.hp = 0

        self.food = max(
            0,
            self.food - dt / 180
        )

        self.attack_cd = max(
            0,
            self.attack_cd - dt
        )


# =========================================================
# MOB
# =========================================================

class Mob:

    def __init__(self, x, y, z, t):

        self.x = x
        self.y = y
        self.z = z
        self.t = t

        self.hp = (
            20
            if t in ("zombie", "creeper")
            else 10
        )

        self.cd = 0

    def update(self, w, p, dt):

        self.cd = max(
            0,
            self.cd - dt
        )

        dx = p.x - self.x
        dz = p.z - self.z

        d = math.hypot(
            dx,
            dz
        )

        if self.t == "zombie" and d < 18:

            if d:

                self.x += (
                    dx / d
                    * 1.2
                    * dt
                )

                self.z += (
                    dz / d
                    * 1.2
                    * dt
                )

            if d < 1.4 and self.cd <= 0:

                p.hp -= 2
                self.cd = 1

        else:

            a = math.sin(
                time.time()
                + self.x
            )

            self.x += (
                a * dt
            )

            self.z += (
                math.cos(
                    time.time()
                    + self.z
                )
                * dt
                * 0.5
            )

        self.y = w.surface(
            self.x,
            self.z
        )


# =========================================================
# GAME
# =========================================================

class Game:

    def __init__(self):

        self.world = World()

        self.p = Player(
            self.world
        )

        self.world.ensure(
            0,
            0,
            3
        )

        self.inv_open = False
        self.craft_open = False
        self.menu = False

        self.last_save = 0

        self.cross = (
            W // 2,
            H // 2
        )

        self.mobs = []

        # TOUCH STATE
        self.touch_points = {}

        self.touch_controls = {
            "left": False,
            "right": False,
            "up": False,
            "down": False
        }

        self.touch_mining = False

        # Camera swipe
        self.camera_finger = None
        self.last_camera_pos = None

        # Prevent touch + mouse double actions
        self.last_touch_action = 0

        for _ in range(10):

            x = random.randint(
                -20,
                20
            )

            z = random.randint(
                -20,
                20
            )

            self.mobs.append(
                Mob(
                    x + 0.5,
                    self.world.surface(
                        x,
                        z
                    ),
                    z + 0.5,
                    random.choice(
                        [
                            "zombie",
                            "sheep",
                            "creeper"
                        ]
                    )
                )
            )

    # =====================================================
    # TOUCH BUTTON RECTANGLES
    # =====================================================

    def touch_buttons(self):

        return {
            "L": pygame.Rect(
                25,
                H - 170,
                90,
                90
            ),

            "R": pygame.Rect(
                130,
                H - 170,
                90,
                90
            ),

            "J": pygame.Rect(
                W - 115,
                H - 155,
                90,
                90
            ),

            "M": pygame.Rect(
                W - 225,
                H - 155,
                90,
                90
            ),

            "P": pygame.Rect(
                W - 335,
                H - 155,
                90,
                90
            ),

            "I": pygame.Rect(
                W - 225,
                H - 265,
                90,
                90
            ),

            "C": pygame.Rect(
                W - 335,
                H - 265,
                90,
                90
            )
        }

    def get_hotbar_rects(self):

        size = min(
            64,
            W // 10
        )

        total = size * len(HOT)

        x = (
            W - total
        ) // 2

        y = (
            H
            - size
            - 20
        )

        rects = []

        for i in range(len(HOT)):

            rects.append(
                pygame.Rect(
                    x + i * size,
                    y,
                    size - 4,
                    size - 4
                )
            )

        return rects

    def touch_button_at(self, pos):

        buttons = self.touch_buttons()

        for name, rect in buttons.items():

            if rect.collidepoint(pos):
                return name

        return None

    # =====================================================
    # TOUCH ACTION
    # =====================================================

    def handle_touch_down(self, finger_id, pos):

        self.last_touch_action = time.time()

        # MENU
        if self.menu:

            self.menu = False
            return

        # INVENTORY / CRAFT PANEL
        if self.inv_open or self.craft_open:

            # Tap outside closes
            panel = pygame.Rect(
                W * 0.12,
                H * 0.12,
                W * 0.76,
                H * 0.65
            )

            if not panel.collidepoint(pos):

                self.inv_open = False
                self.craft_open = False

            elif self.craft_open:

                # Recipe selection
                yy = panel.y + 80

                for i, recipe in enumerate(
                    RECIPES
                ):

                    rect = pygame.Rect(
                        panel.x + 20,
                        yy,
                        panel.w - 40,
                        42
                    )

                    if rect.collidepoint(pos):

                        self.craft(i)
                        break

                    yy += 52

            return

        # HOTBAR
        for i, rect in enumerate(
            self.get_hotbar_rects()
        ):

            if rect.collidepoint(pos):

                self.p.sel = i
                return

        # BUTTON
        button = self.touch_button_at(
            pos
        )

        if button:

            if button == "L":
                self.touch_controls["left"] = True

            elif button == "R":
                self.touch_controls["right"] = True

            elif button == "J":

                if self.p.ground:
                    self.p.vy = 7

            elif button == "M":

                self.touch_mining = True
                self.mine()

            elif button == "P":

                self.place()

            elif button == "I":

                self.inv_open = True
                self.craft_open = False

            elif button == "C":

                self.craft_open = True
                self.inv_open = False

            self.touch_points[
                finger_id
            ] = {
                "button": button,
                "pos": pos
            }

            return

        # CAMERA
        self.camera_finger = finger_id
        self.last_camera_pos = pos

        self.touch_points[
            finger_id
        ] = {
            "button": None,
            "pos": pos
        }

    def handle_touch_motion(self, finger_id, pos):

        state = self.touch_points.get(
            finger_id
        )

        if not state:
            return

        # Do not move camera while
        # pressing a control
        if state.get("button"):
            state["pos"] = pos
            return

        if self.inv_open or self.craft_open:
            return

        if (
            self.camera_finger == finger_id
            and self.last_camera_pos is not None
        ):

            old_x, old_y = (
                self.last_camera_pos
            )

            new_x, new_y = pos

            dx = new_x - old_x
            dy = new_y - old_y

            self.p.yaw += dx * 0.004

            self.p.pitch = max(
                -1.2,
                min(
                    1.2,
                    self.p.pitch
                    - dy * 0.004
                )
            )

            self.last_camera_pos = pos

    def handle_touch_up(self, finger_id):

        state = self.touch_points.pop(
            finger_id,
            None
        )

        if not state:
            return

        button = state.get(
            "button"
        )

        if button == "L":
            self.touch_controls["left"] = False

        elif button == "R":
            self.touch_controls["right"] = False

        elif button == "M":
            self.touch_mining = False

        if self.camera_finger == finger_id:

            self.camera_finger = None
            self.last_camera_pos = None

    # =====================================================
    # PROJECT 3D
    # =====================================================

    def project(self, x, y, z):

        dx = x - self.p.x
        dy = y - self.p.y
        dz = z - self.p.z

        sy = math.sin(
            self.p.yaw
        )

        cy = math.cos(
            self.p.yaw
        )

        rx = (
            cy * dx
            - sy * dz
        )

        rz = (
            sy * dx
            + cy * dz
        )

        rz = max(
            0.2,
            rz
        )

        f = min(
            W,
            H
        ) * 0.9

        sx = (
            W / 2
            + rx / rz * f
        )

        sy2 = (
            H / 2
            - (
                dy * f / rz
            )
            + math.tan(
                self.p.pitch
            ) * f
        )

        return (
            sx,
            sy2,
            rz
        )

    # =====================================================
    # CUBE
    # =====================================================

    def cube(self, x, y, z, b):

        pts = [
            self.project(
                x + dx,
                y + dy,
                z + dz
            )

            for dx, dy, dz in [
                (0, 0, 0),
                (1, 0, 0),
                (1, 1, 0),
                (0, 1, 0),
                (0, 0, 1),
                (1, 0, 1),
                (1, 1, 1),
                (0, 1, 1)
            ]
        ]

        if min(
            q[2]
            for q in pts
        ) > 35:
            return

        c = COL.get(
            b,
            (200, 200, 200)
        )

        faces = [
            ([0, 1, 2, 3], 1.0),
            ([4, 5, 6, 7], 0.78),
            ([3, 2, 6, 7], 1.12),
            ([0, 1, 5, 4], 0.62)
        ]

        for ids, shade in faces:

            poly = [
                (
                    pts[i][0],
                    pts[i][1]
                )
                for i in ids
            ]

            color = tuple(
                max(
                    0,
                    min(
                        255,
                        int(
                            v * shade
                        )
                    )
                )
                for v in c
            )

            pygame.draw.polygon(
                screen,
                color,
                poly
            )

            pygame.draw.polygon(
                screen,
                (30, 30, 30),
                poly,
                1
            )

    # =====================================================
    # RENDER
    # =====================================================

    def render(self):

        sky = (
            (38, 90, 145)
            if (
                self.world.time % 1200
            ) < 600
            else
            (12, 18, 38)
        )

        screen.fill(sky)

        self.world.ensure(
            self.p.x,
            self.p.z,
            2
        )

        visible = []

        for (x, y, z), b in self.world.blocks.items():

            if b == B.AIR:
                continue

            d = (
                (x - self.p.x) ** 2
                + (z - self.p.z) ** 2
            )

            if d < 32 * 32:

                visible.append(
                    (
                        d,
                        (x, y, z),
                        b
                    )
                )

        for _, pos, b in sorted(
            visible,
            reverse=True
        ):

            self.cube(
                *pos,
                b
            )

        # MOBS
        for m in self.mobs:

            sx, sy, d = self.project(
                m.x,
                m.y,
                m.z
            )

            if d < 25:

                if m.t == "sheep":
                    col = (
                        60,
                        180,
                        70
                    )

                elif m.t == "creeper":
                    col = (
                        50,
                        50,
                        50
                    )

                else:
                    col = (
                        80,
                        150,
                        80
                    )

                r = max(
                    5,
                    int(
                        260 / d
                    )
                )

                pygame.draw.rect(
                    screen,
                    col,
                    (
                        sx - r,
                        sy - 2 * r,
                        2 * r,
                        2 * r
                    )
                )

        # CROSSHAIR
        pygame.draw.line(
            screen,
            (245, 245, 245),
            (
                W // 2 - 8,
                H // 2
            ),
            (
                W // 2 + 8,
                H // 2
            ),
            2
        )

        pygame.draw.line(
            screen,
            (245, 245, 245),
            (
                W // 2,
                H // 2 - 8
            ),
            (
                W // 2,
                H // 2 + 8
            ),
            2
        )

        self.ui()

    # =====================================================
    # UI
    # =====================================================

    def ui(self):

        # HP
        pygame.draw.rect(
            screen,
            (25, 25, 25),
            (
                18,
                18,
                230,
                22
            )
        )

        pygame.draw.rect(
            screen,
            (190, 45, 55),
            (
                20,
                20,
                int(
                    226
                    * max(
                        0,
                        self.p.hp
                    ) / 20
                ),
                18
            )
        )

        # FOOD
        pygame.draw.rect(
            screen,
            (25, 25, 25),
            (
                18,
                45,
                230,
                22
            )
        )

        pygame.draw.rect(
            screen,
            (220, 155, 40),
            (
                20,
                47,
                int(
                    226
                    * max(
                        0,
                        self.p.food
                    ) / 20
                ),
                18
            )
        )

        screen.blit(
            small.render(
                f"HP {self.p.hp:.0f}  FOOD {self.p.food:.0f}",
                True,
                (255, 255, 255)
            ),
            (
                25,
                47
            )
        )

        # HOTBAR
        size = min(
            64,
            W // 10
        )

        total = (
            size
            * len(HOT)
        )

        x = (
            W - total
        ) // 2

        y = (
            H
            - size
            - 20
        )

        for i, b in enumerate(HOT):

            r = pygame.Rect(
                x + i * size,
                y,
                size - 4,
                size - 4
            )

            pygame.draw.rect(
                screen,
                (
                    (230, 190, 70)
                    if i == self.p.sel
                    else
                    (35, 35, 40)
                ),
                r
            )

            pygame.draw.rect(
                screen,
                (210, 210, 210),
                r,
                2
            )

            pygame.draw.rect(
                screen,
                COL[b],
                r.inflate(
                    -22,
                    -22
                )
            )

            n = self.p.inv.get(
                b,
                0
            )

            screen.blit(
                small.render(
                    str(n),
                    True,
                    (255, 255, 255)
                ),
                (
                    r.x + 4,
                    r.bottom - 19
                )
            )

        # MOBILE CONTROLS
        self.draw_touch_controls()

        # INVENTORY / CRAFTING
        if (
            self.inv_open
            or self.craft_open
        ):

            panel = pygame.Rect(
                W * 0.12,
                H * 0.12,
                W * 0.76,
                H * 0.65
            )

            pygame.draw.rect(
                screen,
                (24, 24, 28),
                panel
            )

            pygame.draw.rect(
                screen,
                (180, 180, 190),
                panel,
                3
            )

            title = (
                "INVENTORY"
                if self.inv_open
                else
                "CRAFTING"
            )

            screen.blit(
                big.render(
                    title,
                    True,
                    (255, 255, 255)
                ),
                (
                    panel.x + 20,
                    panel.y + 15
                )
            )

            if self.craft_open:

                yy = panel.y + 80

                for name, ing, res in RECIPES:

                    txt = (
                        name
                        + "  "
                        + ", ".join(
                            f"{NAME.get(k, k)}x{v}"
                            for k, v
                            in ing.items()
                        )
                    )

                    pygame.draw.rect(
                        screen,
                        (50, 50, 55),
                        (
                            panel.x + 20,
                            yy,
                            panel.w - 40,
                            42
                        )
                    )

                    screen.blit(
                        small.render(
                            txt,
                            True,
                            (235, 235, 235)
                        ),
                        (
                            panel.x + 30,
                            yy + 12
                        )
                    )

                    yy += 52

            else:

                xx = panel.x + 25
                yy = panel.y + 80

                for b, n in self.p.inv.items():

                    if not isinstance(
                        b,
                        B
                    ):
                        continue

                    screen.blit(
                        small.render(
                            f"{NAME[b]}: {n}",
                            True,
                            (240, 240, 240)
                        ),
                        (
                            xx,
                            yy
                        )
                    )

                    yy += 28

    def draw_touch_controls(self):

        overlay = pygame.Surface(
            (W, H),
            pygame.SRCALPHA
        )

        buttons = self.touch_buttons()

        labels = {
            "L": "◀",
            "R": "▶",
            "J": "JUMP",
            "M": "MINE",
            "P": "PLACE",
            "I": "INV",
            "C": "CRAFT"
        }

        for name, rect in buttons.items():

            active = False

            if name == "L":
                active = self.touch_controls["left"]

            elif name == "R":
                active = self.touch_controls["right"]

            elif name == "M":
                active = self.touch_mining

            if active:
                bg = (
                    255,
                    220,
                    80,
                    190
                )
            else:
                bg = (
                    255,
                    255,
                    255,
                    110
                )

            pygame.draw.circle(
                overlay,
                bg,
                rect.center,
                min(
                    rect.width,
                    rect.height
                ) // 2
            )

            text = font.render(
                labels[name],
                True,
                (20, 20, 20)
            )

            overlay.blit(
                text,
                text.get_rect(
                    center=rect.center
                )
            )

        screen.blit(
            overlay,
            (0, 0)
        )

    # =====================================================
    # BLOCK TARGET
    # =====================================================

    def block_target(self):

        sy = math.sin(
            self.p.yaw
        )

        cy = math.cos(
            self.p.yaw
        )

        cp = math.cos(
            self.p.pitch
        )

        sp = math.sin(
            self.p.pitch
        )

        for i in range(1, 80):

            t = i * 0.08

            x = (
                self.p.x
                + sy * cp * t
            )

            y = (
                self.p.y
                + sp * t
            )

            z = (
                self.p.z
                - cy * cp * t
            )

            pos = (
                math.floor(x),
                math.floor(y),
                math.floor(z)
            )

            b = self.world.get(
                *pos
            )

            if b not in (
                B.AIR,
                B.WATER
            ):

                return pos, b

        return None, None

    # =====================================================
    # MINE
    # =====================================================

    def mine(self):

        pos, b = self.block_target()

        if not pos:
            return

        if self.p.breaking != pos:

            self.p.breaking = pos
            self.p.progress = 0

        power = {
            "hand": 1,
            "wood_pick": 2,
            "stone_pick": 3,
            "iron_pick": 5
        }.get(
            self.p.tool,
            1
        )

        self.p.progress += (
            power
            / max(
                1,
                HARD.get(
                    b,
                    1
                )
            )
        )

        if self.p.progress >= 15:

            self.world.set(
                *pos,
                B.AIR
            )

            drop = DROP.get(
                b,
                b
            )

            self.p.inv[drop] = (
                self.p.inv.get(
                    drop,
                    0
                ) + 1
            )

            self.p.breaking = None
            self.p.progress = 0

    # =====================================================
    # PLACE
    # =====================================================

    def place(self):

        pos, b = self.block_target()

        if not pos:
            return

        x, y, z = pos

        sy = math.sin(
            self.p.yaw
        )

        cy = math.cos(
            self.p.yaw
        )

        cp = math.cos(
            self.p.pitch
        )

        sp = math.sin(
            self.p.pitch
        )

        tx = (
            self.p.x
            + sy * cp * 2.8
        )

        ty = (
            self.p.y
            + sp * 2.8
        )

        tz = (
            self.p.z
            - cy * cp * 2.8
        )

        target = (
            math.floor(tx),
            math.floor(ty),
            math.floor(tz)
        )

        hb = HOT[
            self.p.sel
            % len(HOT)
        ]

        if (
            self.p.inv.get(
                hb,
                0
            ) > 0
            and
            self.world.get(
                *target
            ) == B.AIR
        ):

            self.world.set(
                *target,
                hb
            )

            self.p.inv[hb] -= 1

    # =====================================================
    # CRAFT
    # =====================================================

    def craft(self, idx):

        if not 0 <= idx < len(
            RECIPES
        ):
            return

        _, ing, res = RECIPES[idx]

        possible = True

        for k, v in ing.items():

            if isinstance(k, B):

                if self.p.inv.get(
                    k,
                    0
                ) < v:

                    possible = False

            elif isinstance(k, str):

                # stick is represented
                # by normal inventory
                # only if previously created.
                if self.p.inv.get(
                    k,
                    0
                ) < v:

                    possible = False

        if not possible:
            return

        for k, v in ing.items():

            self.p.inv[k] = (
                self.p.inv.get(
                    k,
                    0
                ) - v
            )

        for k, v in res.items():

            if isinstance(k, B):

                self.p.inv[k] = (
                    self.p.inv.get(
                        k,
                        0
                    ) + v
                )

            elif k == "stick":

                self.p.inv["stick"] = (
                    self.p.inv.get(
                        "stick",
                        0
                    ) + v
                )

            elif k == "tool":

                self.p.tool = v

    # =====================================================
    # SAVE
    # =====================================================

    def save(self):

        if self.world.save(
            self.p
        ):

            self.last_save = (
                time.time()
            )

    # =====================================================
    # EVENTS
    # =====================================================

    def events(self):

        for e in pygame.event.get():

            # QUIT
            if e.type == pygame.QUIT:

                self.save()
                return False

            # KEYBOARD
            if e.type == pygame.KEYDOWN:

                if e.key == pygame.K_ESCAPE:

                    self.menu = not self.menu

                elif e.key == pygame.K_e:

                    self.inv_open = (
                        not self.inv_open
                    )

                    self.craft_open = False

                elif e.key == pygame.K_c:

                    self.craft_open = (
                        not self.craft_open
                    )

                    self.inv_open = False

                elif (
                    e.key == pygame.K_SPACE
                    and self.p.ground
                ):

                    self.p.vy = 7

                elif (
                    pygame.K_1
                    <= e.key
                    <= pygame.K_9
                ):

                    self.p.sel = (
                        e.key
                        - pygame.K_1
                    ) % len(HOT)

                elif e.key == pygame.K_f:

                    self.place()

            # MOUSE CAMERA
            elif e.type == pygame.MOUSEMOTION:

                # Ignore mouse events immediately
                # generated by touch.
                if (
                    time.time()
                    - self.last_touch_action
                    < 0.15
                ):
                    continue

                if (
                    pygame.mouse.get_pressed()[0]
                    and not self.inv_open
                    and not self.craft_open
                ):

                    self.p.yaw += (
                        e.rel[0]
                        * 0.004
                    )

                    self.p.pitch = max(
                        -1.2,
                        min(
                            1.2,
                            self.p.pitch
                            - e.rel[1]
                            * 0.004
                        )
                    )

            # MOUSE
            elif e.type == pygame.MOUSEBUTTONDOWN:

                if (
                    time.time()
                    - self.last_touch_action
                    < 0.15
                ):
                    continue

                if e.button == 1:

                    self.mine()

                elif e.button == 3:

                    self.place()

            # TOUCH DOWN
            elif e.type == pygame.FINGERDOWN:

                pos = (
                    int(e.x * W),
                    int(e.y * H)
                )

                self.handle_touch_down(
                    e.finger_id,
                    pos
                )

            # TOUCH MOTION
            elif e.type == pygame.FINGERMOTION:

                pos = (
                    int(e.x * W),
                    int(e.y * H)
                )

                self.handle_touch_motion(
                    e.finger_id,
                    pos
                )

            # TOUCH UP
            elif e.type == pygame.FINGERUP:

                self.handle_touch_up(
                    e.finger_id
                )

        return True

    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        running = True

        while running:

            dt = min(
                0.05,
                clock.tick(60) / 1000
            )

            running = self.events()

            if not running:
                break

            keys = pygame.key.get_pressed()

            if (
                not self.inv_open
                and not self.craft_open
                and not self.menu
            ):

                self.p.update(
                    self.world,
                    dt,
                    keys,
                    self.touch_controls
                )

                # Continuous mining while
                # holding M on touchscreen.
                if self.touch_mining:

                    self.mine()

                for m in self.mobs:

                    m.update(
                        self.world,
                        self.p,
                        dt
                    )

                self.world.time += dt

            # AUTO SAVE
            if (
                time.time()
                - self.last_save
                > 20
            ):

                self.save()

            self.render()

            pygame.display.flip()

        self.save()

        pygame.quit()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    try:
        Game().run()

    except Exception as exc:

        # Save crash information when possible.
        try:

            with open(
                "crash.log",
                "w"
            ) as f:

                f.write(
                    "minecraftKw v1 crash\n\n"
                )

                f.write(
                    repr(exc)
                )

        except Exception:
            pass

        raise
