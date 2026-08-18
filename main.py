import pygame
import math
import random
import json
import os
import time
from enum import IntEnum

pygame.init()

try:
    pygame.mixer.init()
except Exception:
    pass

info = pygame.display.Info()
W = info.current_w or 1280
H = info.current_h or 720

screen = pygame.display.set_mode(
    (W, H),
    pygame.FULLSCREEN | pygame.SCALED
)

pygame.display.set_caption("minecraftKw v1")
clock = pygame.time.Clock()

font = pygame.font.Font(None, max(22, H // 32))
small = pygame.font.Font(None, max(18, H // 42))
big = pygame.font.Font(None, max(34, H // 20))


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

NAME = {b: b.name.title() for b in B}

SOLID = {b: True for b in B}
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
    ("Planks", {B.WOOD: 1}, {B.PLANK: 4}),
    ("Stick", {B.PLANK: 2}, {"stick": 4}),
    ("Wood Pick", {B.PLANK: 3, "stick": 2}, {"tool": "wood_pick"}),
    ("Stone Pick", {B.COBBLE: 3, "stick": 2}, {"tool": "stone_pick"}),
    ("Iron Pick", {B.IRON: 3, "stick": 2}, {"tool": "iron_pick"}),
    ("Glass", {B.SAND: 1}, {B.GLASS: 1}),
]

SAVE_DIR = "saves"
os.makedirs(SAVE_DIR, exist_ok=True)


class World:
    def __init__(self, seed=None):
        self.seed = seed or random.randrange(1, 2 ** 31)
        self.blocks = {}
        self.time = 0
        self.generated = set()

    def noise(self, x, z):
        r = random.Random(
            (self.seed * 73856093 +
             x * 19349663 +
             z * 83492791) & 0xffffffff
        )
        return r.random()

    def gen_chunk(self, cx, cz):
        if (cx, cz) in self.generated:
            return

        self.generated.add((cx, cz))

        rng = random.Random(
            self.seed + cx * 991 + cz * 313
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
                            n * 5 +
                            self.noise(x // 3, z // 3) * 2
                        )
                    )
                )

                beach = h <= 6

                for y in range(h):
                    if y < h - 4:
                        b = B.STONE
                    else:
                        b = B.SAND if beach else B.DIRT

                    self.blocks[(x, y, z)] = b

                self.blocks[(x, h, z)] = (
                    B.SAND if beach else B.GRASS
                )

                if h > 7 and rng.random() < 0.035:
                    for y in range(h + 1, h + 5):
                        self.blocks[(x, y, z)] = B.LOG

                    for dx in range(-2, 3):
                        for dz in range(-2, 3):
                            if dx * dx + dz * dz < 7:
                                self.blocks[
                                    (x + dx, h + 5, z + dz)
                                ] = B.LEAVES

                if rng.random() < 0.06:
                    oy = rng.randint(2, max(2, h - 4))

                    self.blocks[(x, oy, z)] = (
                        B.COAL if rng.random() < 0.6 else B.IRON
                    )

                if beach and rng.random() < 0.025:
                    self.blocks[(x, h, z)] = B.WATER

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
            (int(x), int(y), int(z)),
            B.AIR
        )

    def set(self, x, y, z, b):
        if 0 <= y < 128:
            self.blocks[
                (int(x), int(y), int(z))
            ] = b

    def surface(self, x, z):
        for y in range(127, 0, -1):
            if SOLID.get(
                self.get(x, y, z),
                False
            ):
                return y + 1

        return 10

    def save(self, player, slot="world.json"):
        data = {
            "seed": self.seed,
            "time": self.time,
            "player": player.pack(),
            "blocks": [
                [x, y, z, b.value]
                for (x, y, z), b in self.blocks.items()
            ],
        }

        with open(
            os.path.join(SAVE_DIR, slot),
            "w"
        ) as f:
            json.dump(data, f)

    def load(self, player, slot="world.json"):
        path = os.path.join(
            SAVE_DIR,
            slot
        )

        if not os.path.exists(path):
            return False

        with open(path) as f:
            data = json.load(f)

        self.seed = data["seed"]
        self.time = data.get("time", 0)

        self.blocks = {
            (a, b, c): B(v)
            for a, b, c, v
            in data.get("blocks", [])
        }

        self.generated = set()

        player.unpack(
            data.get("player", {})
        )

        return True


class Player:
    def __init__(self, world):
        self.x = 0.5
        self.z = 0.5
        self.y = world.surface(0, 0)

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
            B.STONE: 4,
        }

        self.tools = {
            "hand": 999,
            "wood_pick": 60,
            "stone_pick": 132,
            "iron_pick": 251,
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
                str(int(k)) if isinstance(k, B) else str(k): v
                for k, v in self.inv.items()
            },
            "tools": self.tools,
            "tool": self.tool,
            "sel": self.sel,
        }

    def unpack(self, d):
        for k in (
            "x",
            "y",
            "z",
            "yaw",
            "pitch",
            "hp",
            "food",
        ):
            if k in d:
                setattr(self, k, d[k])

        self.inv = {}

        for k, v in d.get("inv", {}).items():
            try:
                self.inv[B(int(k))] = v
            except Exception:
                self.inv[k] = v

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

    def solid_at(self, world, x, y, z):
        return SOLID.get(
            world.get(
                math.floor(x),
                math.floor(y),
                math.floor(z)
            ),
            False
        )

    def move(self, world, dx, dz):
        nx = self.x + dx
        nz = self.z + dz

        blocked = any(
            self.solid_at(
                world,
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

    def update(self, world, dt, keys):
        world.ensure(
            self.x,
            self.z,
            2
        )

        speed = 4.2 * dt

        f = (
            keys[pygame.K_w]
            - keys[pygame.K_s]
        )

        s = (
            keys[pygame.K_d]
            - keys[pygame.K_a]
        )

        ln = math.hypot(f, s) or 1

        sy = math.sin(self.yaw)
        cy = math.cos(self.yaw)

        self.move(
            world,
            (sy * f + cy * s) / ln * speed,
            (-cy * f + sy * s) / ln * speed
        )

        self.vy -= 18 * dt

        ny = self.y + self.vy * dt

        if (
            self.vy < 0
            and self.solid_at(
                world,
                self.x,
                ny - 0.9,
                self.z
            )
        ):
            self.y = math.floor(ny) + 1
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

    def update(self, world, player, dt):
        self.cd = max(
            0,
            self.cd - dt
        )

        dx = player.x - self.x
        dz = player.z - self.z

        d = math.hypot(dx, dz)

        if self.t == "zombie" and d < 18:
            if d:
                self.x += (
                    dx / d * 1.2 * dt
                )
                self.z += (
                    dz / d * 1.2 * dt
                )

            if d < 1.4 and self.cd <= 0:
                player.hp -= 2
                self.cd = 1

        else:
            a = math.sin(
                time.time() + self.x
            )

            self.x += a * dt

            self.z += (
                math.cos(
                    time.time() + self.z
                ) * dt * 0.5
            )

        self.y = world.surface(
            self.x,
            self.z
        )


class Game:
    def __init__(self):
        self.world = World()
        self.p = Player(self.world)

        self.world.ensure(
            0,
            0,
            3
        )

        self.inv_open = False
        self.craft_open = False
        self.menu = False

        self.last_save = 0

        self.mobs = []

        for _ in range(10):
            x = random.randint(-20, 20)
            z = random.randint(-20, 20)

            self.mobs.append(
                Mob(
                    x + 0.5,
                    self.world.surface(x, z),
                    z + 0.5,
                    random.choice([
                        "zombie",
                        "sheep",
                        "creeper"
                    ])
                )
            )

        # -----------------------------
        # TOUCH CONTROL
        # -----------------------------

        self.fingers = {}

        self.move_finger = None
        self.look_finger = None

        self.move_center = (
            110,
            H - 130
        )

        self.move_radius = 82

        self.move_vector = [0, 0]

        self.look_last = None

        self.touch_mine_timer = 0

    # ---------------------------------
    # TOUCH BUTTON RECTANGLES
    # ---------------------------------

    def touch_buttons(self):
        return {
            "jump": pygame.Rect(
                W - 150,
                H - 150,
                90,
                90
            ),

            "mine": pygame.Rect(
                W - 270,
                H - 150,
                90,
                90
            ),

            "place": pygame.Rect(
                W - 390,
                H - 150,
                90,
                90
            ),

            "inventory": pygame.Rect(
                W - 150,
                H - 270,
                90,
                75
            ),

            "craft": pygame.Rect(
                W - 270,
                H - 270,
                90,
                75
            ),
        }

    # ---------------------------------
    # PROJECTION
    # ---------------------------------

    def project(self, x, y, z):
        dx = x - self.p.x
        dy = y - self.p.y
        dz = z - self.p.z

        sy = math.sin(self.p.yaw)
        cy = math.cos(self.p.yaw)

        rx = cy * dx - sy * dz
        rz = sy * dx + cy * dz

        rz = max(
            0.2,
            rz
        )

        f = min(W, H) * 0.9

        sx = W / 2 + rx / rz * f

        sy2 = (
            H / 2
            - dy * f / rz
            + math.tan(self.p.pitch) * f
        )

        return sx, sy2, rz

    # ---------------------------------
    # DRAW BLOCK
    # ---------------------------------

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
                (0, 1, 1),
            ]
        ]

        if min(
            q[2] for q in pts
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
            ([0, 1, 5, 4], 0.62),
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
                        int(v * shade)
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

    # ---------------------------------
    # RENDER
    # ---------------------------------

    def render(self):
        if (
            self.world.time % 1200
        ) < 600:
            sky = (38, 90, 145)
        else:
            sky = (12, 18, 38)

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
                    (d, (x, y, z), b)
                )

        for _, pos, b in sorted(
            visible,
            reverse=True
        ):
            self.cube(
                *pos,
                b
            )

        for mob in self.mobs:
            sx, sy, d = self.project(
                mob.x,
                mob.y,
                mob.z
            )

            if d < 25:
                if mob.t == "sheep":
                    col = (60, 180, 70)
                elif mob.t == "creeper":
                    col = (50, 50, 50)
                else:
                    col = (80, 150, 80)

                r = max(
                    5,
                    int(260 / d)
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

        # crosshair
        pygame.draw.line(
            screen,
            (245, 245, 245),
            (W // 2 - 8, H // 2),
            (W // 2 + 8, H // 2),
            2
        )

        pygame.draw.line(
            screen,
            (245, 245, 245),
            (W // 2, H // 2 - 8),
            (W // 2, H // 2 + 8),
            2
        )

        self.ui()

    # ---------------------------------
    # UI
    # ---------------------------------

    def ui(self):
        # HP
        pygame.draw.rect(
            screen,
            (25, 25, 25),
            (18, 18, 230, 22)
        )

        pygame.draw.rect(
            screen,
            (190, 45, 55),
            (
                20,
                20,
                int(
                    226 *
                    max(0, self.p.hp) /
                    20
                ),
                18
            )
        )

        # FOOD
        pygame.draw.rect(
            screen,
            (25, 25, 25),
            (18, 45, 230, 22)
        )

        pygame.draw.rect(
            screen,
            (220, 155, 40),
            (
                20,
                47,
                int(
                    226 *
                    max(0, self.p.food) /
                    20
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
            (25, 47)
        )

        # HOTBAR
        size = min(
            64,
            W // 10
        )

        total = size * len(HOT)

        x = (W - total) // 2
        y = H - size - 20

        for i, b in enumerate(HOT):
            r = pygame.Rect(
                x + i * size,
                y,
                size - 4,
                size - 4
            )

            selected = (
                i == self.p.sel
            )

            pygame.draw.rect(
                screen,
                (230, 190, 70)
                if selected
                else (35, 35, 40),
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
                r.inflate(-22, -22)
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

        self.draw_touch_controls()

        if self.inv_open or self.craft_open:
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
                else "CRAFTING"
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
                    parts = []

                    for k, v in ing.items():
                        label = (
                            NAME.get(k, str(k))
                        )

                        parts.append(
                            f"{label}x{v}"
                        )

                    txt = (
                        name
                        + "  "
                        + ", ".join(parts)
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

                for item, n in self.p.inv.items():
                    label = NAME.get(
                        item,
                        str(item).title()
                    )

                    screen.blit(
                        small.render(
                            f"{label}: {n}",
                            True,
                            (240, 240, 240)
                        ),
                        (xx, yy)
                    )

                    yy += 28

    # ---------------------------------
    # TOUCH UI
    # ---------------------------------

    def draw_touch_controls(self):
        overlay = pygame.Surface(
            (W, H),
            pygame.SRCALPHA
        )

        # joystick base
        pygame.draw.circle(
            overlay,
            (255, 255, 255, 75),
            self.move_center,
            self.move_radius
        )

        # joystick knob
        knob_x = (
            self.move_center[0]
            + self.move_vector[0] * 45
        )

        knob_y = (
            self.move_center[1]
            + self.move_vector[1] * 45
        )

        pygame.draw.circle(
            overlay,
            (255, 255, 255, 130),
            (
                int(knob_x),
                int(knob_y)
            ),
            30
        )

        buttons = self.touch_buttons()

        labels = {
            "jump": "JUMP",
            "mine": "MINE",
            "place": "PLACE",
            "inventory": "INV",
            "craft": "CRAFT",
        }

        for name, rect in buttons.items():
            pygame.draw.rect(
                overlay,
                (255, 255, 255, 75),
                rect,
                border_radius=18
            )

            pygame.draw.rect(
                overlay,
                (255, 255, 255, 130),
                rect,
                2,
                border_radius=18
            )

            text = small.render(
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

    # ---------------------------------
    # BLOCK TARGET
    # ---------------------------------

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

    # ---------------------------------
    # MINE
    # ---------------------------------

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
            "iron_pick": 5,
        }.get(
            self.p.tool,
            1
        )

        self.p.progress += (
            power /
            max(
                1,
                HARD.get(b, 1)
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

    # ---------------------------------
    # PLACE
    # ---------------------------------

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
            max(
                0,
                min(
                    len(HOT) - 1,
                    self.p.sel
                )
            )
        ]

        if (
            self.p.inv.get(hb, 0) > 0
            and self.world.get(*target) == B.AIR
        ):
            self.world.set(
                *target,
                hb
            )

            self.p.inv[hb] -= 1

    # ---------------------------------
    # CRAFT
    # ---------------------------------

    def craft(self, idx):
        if not 0 <= idx < len(RECIPES):
            return

        _, ingredients, result = RECIPES[idx]

        for item, amount in ingredients.items():
            if self.p.inv.get(
                item,
                0
            ) < amount:
                return

        for item, amount in ingredients.items():
            self.p.inv[item] = (
                self.p.inv.get(item, 0)
                - amount
            )

        for item, amount in result.items():
            if item == "tool":
                self.p.tool = amount
            else:
                self.p.inv[item] = (
                    self.p.inv.get(item, 0)
                    + amount
                )

    # ---------------------------------
    # SAVE
    # ---------------------------------

    def save(self):
        self.world.save(
            self.p
        )

        self.last_save = time.time()

    # ---------------------------------
    # TOUCH HANDLER
    # ---------------------------------

    def handle_touch_down(self, fid, pos):
        x, y = pos

        # joystick
        dx = x - self.move_center[0]
        dy = y - self.move_center[1]

        if math.hypot(dx, dy) <= self.move_radius:
            self.move_finger = fid
            self.update_joystick(x, y)
            return

        buttons = self.touch_buttons()

        if buttons["jump"].collidepoint(x, y):
            if self.p.ground:
                self.p.vy = 7
            return

        if buttons["mine"].collidepoint(x, y):
            self.mine()
            self.touch_mine_timer = 0
            self.fingers[fid] = {
                "type": "mine"
            }
            return

        if buttons["place"].collidepoint(x, y):
            self.place()
            return

        if buttons["inventory"].collidepoint(x, y):
            self.inv_open = not self.inv_open
            self.craft_open = False
            return

        if buttons["craft"].collidepoint(x, y):
            self.craft_open = not self.craft_open
            self.inv_open = False
            return

        # hotbar
        size = min(
            64,
            W // 10
        )

        total = size * len(HOT)

        hx = (W - total) // 2
        hy = H - size - 20

        hotbar_rect = pygame.Rect(
            hx,
            hy,
            total,
            size
        )

        if hotbar_rect.collidepoint(x, y):
            idx = int(
                (x - hx) / size
            )

            if 0 <= idx < len(HOT):
                self.p.sel = idx

            return

        # right side = camera
        if x > W * 0.45:
            self.look_finger = fid
            self.look_last = (
                x,
                y
            )

    def update_joystick(self, x, y):
        dx = x - self.move_center[0]
        dy = y - self.move_center[1]

        length = math.hypot(
            dx,
            dy
        )

        if length > self.move_radius:
            dx *= (
                self.move_radius /
                length
            )

            dy *= (
                self.move_radius /
                length
            )

        self.move_vector = [
            dx / self.move_radius,
            dy / self.move_radius
        ]

    def handle_touch_motion(self, fid, pos):
        x, y = pos

        if fid == self.move_finger:
            self.update_joystick(
                x,
                y
            )
            return

        if fid == self.look_finger:
            if self.look_last is not None:
                old_x, old_y = self.look_last

                self.p.yaw += (
                    (x - old_x) * 0.006
                )

                self.p.pitch -= (
                    (y - old_y) * 0.006
                )

                self.p.pitch = max(
                    -1.2,
                    min(
                        1.2,
                        self.p.pitch
                    )
                )

            self.look_last = (
                x,
                y
            )

    def handle_touch_up(self, fid):
        if fid == self.move_finger:
            self.move_finger = None
            self.move_vector = [
                0,
                0
            ]

        if fid == self.look_finger:
            self.look_finger = None
            self.look_last = None

        self.fingers.pop(
            fid,
            None
        )

    # ---------------------------------
    # EVENTS
    # ---------------------------------

    def events(self, dt):
        for e in pygame.event.get():

            if e.type == pygame.QUIT:
                self.save()
                return False

            if e.type == pygame.KEYDOWN:

                if e.key == pygame.K_ESCAPE:
                    self.menu = not self.menu

                elif e.key == pygame.K_e:
                    self.inv_open = not self.inv_open
                    self.craft_open = False

                elif e.key == pygame.K_c:
                    self.craft_open = not self.craft_open
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
                        e.key -
                        pygame.K_1
                    )

                elif e.key == pygame.K_f:
                    self.place()

            elif (
                e.type == pygame.MOUSEMOTION
                and pygame.mouse.get_pressed()[0]
                and not (
                    self.inv_open
                    or self.craft_open
                )
            ):
                self.p.yaw += (
                    e.rel[0] * 0.004
                )

                self.p.pitch = max(
                    -1.2,
                    min(
                        1.2,
                        self.p.pitch
                        - e.rel[1] * 0.004
                    )
                )

            elif e.type == pygame.MOUSEBUTTONDOWN:

                if e.button == 1:
                    self.mine()

                elif e.button == 3:
                    self.place()

            # Android / pygame touch
            elif e.type == pygame.FINGERDOWN:
                self.handle_touch_down(
                    e.finger_id,
                    (
                        e.x * W,
                        e.y * H
                    )
                )

            elif e.type == pygame.FINGERMOTION:
                self.handle_touch_motion(
                    e.finger_id,
                    (
                        e.x * W,
                        e.y * H
                    )
                )

            elif e.type == pygame.FINGERUP:
                self.handle_touch_up(
                    e.finger_id
                )

        # continuous touch mining
        for fid, data in list(
            self.fingers.items()
        ):
            if data.get("type") == "mine":
                self.touch_mine_timer -= dt

                if self.touch_mine_timer <= 0:
                    self.mine()
                    self.touch_mine_timer = 0.12

        return True

    # ---------------------------------
    # RUN
    # ---------------------------------

    def run(self):
        while True:
            dt = min(
                0.05,
                clock.tick(60) / 1000
            )

            if not self.events(dt):
                break

            keys = pygame.key.get_pressed()

            if not (
                self.inv_open
                or self.craft_open
                or self.menu
            ):
                # keyboard movement
                f = (
                    keys[pygame.K_w]
                    - keys[pygame.K_s]
                )

                s = (
                    keys[pygame.K_d]
                    - keys[pygame.K_a]
                )

                # touch joystick movement
                if self.move_finger is not None:
                    f = -self.move_vector[1]
                    s = self.move_vector[0]

                self.p.update(
                    self.world,
                    dt,
                    {
                        pygame.K_w: 1 if f > 0.15 else 0,
                        pygame.K_s: 1 if f < -0.15 else 0,
                        pygame.K_a: 1 if s < -0.15 else 0,
                        pygame.K_d: 1 if s > 0.15 else 0,
                    }
                )

                for mob in self.mobs:
                    mob.update(
                        self.world,
                        self.p,
                        dt
                    )

                self.world.time += dt

            if (
                time.time() -
                self.last_save
                > 20
            ):
                self.save()

            self.render()

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
