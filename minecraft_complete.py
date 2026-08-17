import pygame
import numpy as np
import math
import random
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, List

pygame.init()
pygame.mixer.init()

# ============= DISPLAY =============
display = (1600, 900)
screen = pygame.display.set_mode(display)
pygame.display.set_caption("MiniCraft - Complete Edition")
clock = pygame.time.Clock()
font_tiny = pygame.font.Font(None, 16)
font_small = pygame.font.Font(None, 20)
font_medium = pygame.font.Font(None, 28)
font_large = pygame.font.Font(None, 36)

# ============= CONSTANTS =============
BLOCK_SIZE = 1.0
VIEW_DISTANCE = 12
RENDER_DISTANCE = 25
DAY_LENGTH = 1200  # 20 minutes = 1 day
HUNGER_DRAIN = 0.5  # per minute
HEALTH_REGEN_THRESHOLD = 17  # need 17+ hunger to regen

class BlockType(Enum):
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3
    WOOD = 4
    LEAVES = 5
    SAND = 6
    GRAVEL = 7
    COBBLESTONE = 8
    OAK_LOG = 9
    WATER = 10
    LAVA = 11

class ToolType(Enum):
    HAND = 0
    WOODEN_PICKAXE = 1
    STONE_PICKAXE = 2
    IRON_PICKAXE = 3

BLOCK_DATA = {
    BlockType.AIR: {"name": "Air", "color": (135, 206, 235), "solid": False, "durability": 0},
    BlockType.GRASS: {"name": "Grass", "color": (34, 139, 34), "solid": True, "durability": 1},
    BlockType.DIRT: {"name": "Dirt", "color": (139, 90, 43), "solid": True, "durability": 1},
    BlockType.STONE: {"name": "Stone", "color": (128, 128, 128), "solid": True, "durability": 3},
    BlockType.WOOD: {"name": "Wood", "color": (139, 69, 19), "solid": True, "durability": 2},
    BlockType.LEAVES: {"name": "Leaves", "color": (34, 139, 34), "solid": True, "durability": 1},
    BlockType.SAND: {"name": "Sand", "color": (238, 214, 175), "solid": True, "durability": 1},
    BlockType.GRAVEL: {"name": "Gravel", "color": (160, 160, 160), "solid": True, "durability": 2},
    BlockType.COBBLESTONE: {"name": "Cobblestone", "color": (102, 102, 102), "solid": True, "durability": 4},
    BlockType.OAK_LOG: {"name": "Oak Log", "color": (101, 67, 33), "solid": True, "durability": 2},
    BlockType.WATER: {"name": "Water", "color": (0, 119, 182), "solid": False, "durability": 0},
    BlockType.LAVA: {"name": "Lava", "color": (255, 140, 0), "solid": False, "durability": 0},
}

TOOL_STATS = {
    ToolType.HAND: {"speed": 0.5, "power": 0.5, "durability": float('inf')},
    ToolType.WOODEN_PICKAXE: {"speed": 1.5, "power": 2, "durability": 60},
    ToolType.STONE_PICKAXE: {"speed": 2.0, "power": 3, "durability": 132},
    ToolType.IRON_PICKAXE: {"speed": 3.0, "power": 4, "durability": 251},
}

RECIPES = {
    "wooden_pickaxe": {
        "ingredients": {BlockType.WOOD: 3},
        "result": ToolType.WOODEN_PICKAXE,
        "result_name": "Wooden Pickaxe"
    },
    "stone_pickaxe": {
        "ingredients": {BlockType.STONE: 3},
        "result": ToolType.STONE_PICKAXE,
        "result_name": "Stone Pickaxe"
    },
    "chest": {
        "ingredients": {BlockType.WOOD: 8},
        "result": BlockType.WOOD,
        "result_name": "Chest"
    },
}

# ============= MOB CLASS =============
class Mob:
    def __init__(self, x, y, z, mob_type="zombie"):
        self.x = x
        self.y = y
        self.z = z
        self.mob_type = mob_type
        self.health = 20 if mob_type == "zombie" else 10
        self.speed = 0.05
        self.direction = random.uniform(0, 2*np.pi)
        self.wander_timer = 0
        self.color = (100, 150, 100) if mob_type == "sheep" else (0, 100, 0)
    
    def update(self, player, world):
        # Wander AI
        self.wander_timer += 1
        if self.wander_timer > 60:
            self.direction = random.uniform(0, 2*np.pi)
            self.wander_timer = 0
        
        # Move
        self.x += np.sin(self.direction) * self.speed
        self.z += np.cos(self.direction) * self.speed
        
        # Simple gravity
        block_below = world.get_block(int(self.x), int(self.y - 1), int(self.z))
        if not BLOCK_DATA[block_below]["solid"]:
            self.y -= 0.2
        
        # Chase player if zombie
        if self.mob_type == "zombie":
            dist = math.sqrt((self.x - player.x)**2 + (self.z - player.z)**2)
            if dist < 15:
                angle = math.atan2(player.z - self.z, player.x - self.x)
                self.x += np.cos(angle) * self.speed * 1.5
                self.z += np.sin(angle) * self.speed * 1.5
    
    def take_damage(self, damage):
        self.health -= damage
        return self.health <= 0

# ============= WORLD CLASS =============
class World:
    def __init__(self):
        self.blocks = {}
        self.mobs = []
        self.generate_world()
    
    def generate_world(self):
        """Advanced terrain generation"""
        for x in range(-30, 31):
            for z in range(-30, 31):
                # Perlin-like noise untuk height
                height = 8 + int(4 * np.sin(x * 0.2) * np.cos(z * 0.2))
                
                for y in range(0, height):
                    if y < 2:
                        self.set_block(x, y, z, BlockType.STONE)
                    elif y < height - 1:
                        if y < 4:
                            self.set_block(x, y, z, BlockType.DIRT if random.random() > 0.1 else BlockType.GRAVEL)
                        else:
                            self.set_block(x, y, z, BlockType.DIRT)
                    else:
                        self.set_block(x, y, z, BlockType.GRASS)
                
                # Trees
                if random.random() < 0.05 and height > 5:
                    tree_h = random.randint(4, 6)
                    for ty in range(height, height + tree_h):
                        self.set_block(x, ty, z, BlockType.OAK_LOG)
                    for ox in range(-2, 3):
                        for oz in range(-2, 3):
                            if (ox*ox + oz*oz) < 9:
                                self.set_block(x+ox, height+tree_h, z+oz, BlockType.LEAVES)
                
                # Water lakes
                if random.random() < 0.02 and height < 6:
                    for oy in range(height, height + 2):
                        self.set_block(x, oy, z, BlockType.WATER)
                
                # Spawn mobs
                if random.random() < 0.01:
                    mob_type = random.choice(["zombie", "sheep", "creeper"])
                    self.mobs.append(Mob(x + 0.5, height + 2, z + 0.5, mob_type))
    
    def set_block(self, x, y, z, block_type):
        if 0 <= y < 256:
            self.blocks[(x, y, z)] = block_type
    
    def get_block(self, x, y, z):
        if 0 <= y < 256:
            return self.blocks.get((x, y, z), BlockType.AIR)
        return BlockType.AIR
    
    def get_visible_blocks(self, px, py, pz, distance):
        result = []
        for (x, y, z), block_type in self.blocks.items():
            if abs(x-px) <= distance and abs(y-py) <= distance and abs(z-pz) <= distance:
                if block_type != BlockType.AIR:
                    result.append(((x, y, z), block_type))
        return result
    
    def save(self, filename="world.sav"):
        data = {
            "blocks": {str(k): v.value for k, v in self.blocks.items()},
            "mobs": []
        }
        os.makedirs("saves", exist_ok=True)
        with open(f"saves/{filename}", "w") as f:
            json.dump(data, f)
    
    def load(self, filename="world.sav"):
        try:
            with open(f"saves/{filename}", "r") as f:
                data = json.load(f)
                self.blocks = {}
                for k, v in data.get("blocks", {}).items():
                    key = eval(k)
                    self.blocks[key] = BlockType(v)
        except:
            pass

# ============= PLAYER CLASS =============
class Player:
    def __init__(self):
        self.x = 0
        self.y = 15
        self.z = 0
        self.yaw = 0
        self.pitch = 0
        self.speed = 0.15
        self.velocity_y = 0
        self.on_ground = False
        
        # Survival stats
        self.health = 20
        self.hunger = 20
        self.saturation = 5
        self.oxygen = 300  # for underwater
        
        # Tools & inventory
        self.tool = ToolType.HAND
        self.inventory = {
            BlockType.DIRT: 64,
            BlockType.WOOD: 32,
            BlockType.STONE: 16,
        }
        self.hotbar = [BlockType.DIRT, BlockType.WOOD, BlockType.STONE, BlockType.GRASS, None]
        self.selected_slot = 0
        
        # Mining
        self.mining_progress = 0
        self.mining_block = None
        self.mining_time = 0
    
    def update(self, keys, world, delta_time):
        # Movement
        if keys[pygame.K_w]:
            self.x += np.sin(self.yaw) * self.speed
            self.z -= np.cos(self.yaw) * self.speed
        if keys[pygame.K_s]:
            self.x -= np.sin(self.yaw) * self.speed
            self.z += np.cos(self.yaw) * self.speed
        if keys[pygame.K_a]:
            self.x -= np.cos(self.yaw) * self.speed
            self.z -= np.sin(self.yaw) * self.speed
        if keys[pygame.K_d]:
            self.x += np.cos(self.yaw) * self.speed
            self.z += np.sin(self.yaw) * self.speed
        
        # Jump
        if keys[pygame.K_SPACE] and self.on_ground:
            self.velocity_y = 0.6
            self.on_ground = False
        
        # Gravity
        self.velocity_y -= 0.03
        self.y += self.velocity_y
        
        # Collision
        block_below = world.get_block(int(self.x), int(self.y - 1.6), int(self.z))
        if BLOCK_DATA[block_below]["solid"]:
            self.y = int(self.y) + 1.6
            self.velocity_y = 0
            self.on_ground = True
        else:
            self.on_ground = False
        
        if self.y < 0:
            self.y = 0
            self.velocity_y = 0
        
        # Survival mechanics
        self.hunger = max(0, self.hunger - HUNGER_DRAIN * delta_time)
        
        if self.hunger > 0:
            self.health = min(20, self.health + 0.01)
        elif self.hunger == 0:
            self.health -= 0.05
        
        if self.health <= 0:
            self.respawn()
    
    def respawn(self):
        self.health = 20
        self.hunger = 20
        self.x = 0
        self.y = 15
        self.z = 0
    
    def get_look_direction(self):
        return np.array([
            np.sin(self.yaw) * np.cos(self.pitch),
            np.sin(self.pitch),
            -np.cos(self.yaw) * np.cos(self.pitch)
        ])
    
    def raycast(self, world, max_distance=6):
        direction = self.get_look_direction()
        pos = np.array([self.x, self.y - 1.6, self.z])
        
        for i in range(int(max_distance * 10)):
            check_pos = pos + direction * (i * 0.1)
            block_pos = tuple(np.round(check_pos).astype(int))
            block = world.get_block(*block_pos)
            
            if block != BlockType.AIR and BLOCK_DATA[block]["solid"]:
                return block_pos
        
        return None
    
    def break_block(self, world, world_time):
        target = self.raycast(world)
        if not target:
            self.mining_progress = 0
            self.mining_block = None
            return
        
        if self.mining_block != target:
            self.mining_block = target
            self.mining_progress = 0
            self.mining_time = 0
        
        block_type = world.get_block(*target)
        if block_type == BlockType.AIR:
            return
        
        # Calculate mining time
        tool_speed = TOOL_STATS[self.tool]["speed"]
        block_durability = BLOCK_DATA[block_type]["durability"]
        mining_time_needed = (block_durability / tool_speed) * 20  # frames
        
        self.mining_progress += 1
        self.mining_time += 1
        
        if self.mining_time >= mining_time_needed:
            world.set_block(*target, BlockType.AIR)
            self.inventory[block_type] = self.inventory.get(block_type, 0) + 1
            self.mining_progress = 0
            self.mining_block = None
            self.mining_time = 0
    
    def place_block(self, world):
        target = self.raycast(world)
        if not target:
            return
        
        selected_block = self.hotbar[self.selected_slot]
        if selected_block is None or self.inventory.get(selected_block, 0) <= 0:
            return
        
        direction = self.get_look_direction()
        placed_pos = (
            target[0] + int(np.sign(direction[0]) if direction[0] != 0 else 1),
            target[1] + int(np.sign(direction[1]) if direction[1] != 0 else 0),
            target[2] + int(np.sign(direction[2]) if direction[2] != 0 else 1)
        )
        
        # Don't place on player
        if abs(placed_pos[0] - self.x) > 1 or abs(placed_pos[1] - (self.y-1.6)) > 1 or abs(placed_pos[2] - self.z) > 1:
            world.set_block(*placed_pos, selected_block)
            self.inventory[selected_block] -= 1
    
    def eat(self):
        if self.hunger < 20:
            self.hunger = min(20, self.hunger + 5)
            self.saturation = min(30, self.saturation + 2.5)

# ============= RENDERER =============
class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height))
    
    def clear(self, color):
        self.surface.fill(color)
    
    def get_sky_color(self, time_of_day):
        """Calculate sky color based on time"""
        # 0 = midnight (dark), 0.25 = sunrise, 0.5 = noon, 0.75 = sunset, 1 = midnight
        t = (time_of_day % 1)
        
        if t < 0.25:
            # Night to sunrise
            progress = t / 0.25
            return (
                int(20 + 115 * progress),
                int(20 + 186 * progress),
                int(40 + 195 * progress)
            )
        elif t < 0.5:
            # Sunrise to noon
            progress = (t - 0.25) / 0.25
            return (
                int(135 + 100 * progress),
                int(206 + 49 * progress),
                int(235)
            )
        elif t < 0.75:
            # Noon to sunset
            progress = (t - 0.5) / 0.25
            return (
                int(235 - 100 * progress),
                int(255 - 49 * progress),
                int(235 - 100 * progress)
            )
        else:
            # Sunset to night
            progress = (t - 0.75) / 0.25
            return (
                int(135 - 115 * progress),
                int(206 - 186 * progress),
                int(135 - 95 * progress)
            )
    
    def get_block_light(self, time_of_day):
        """Get brightness multiplier based on time"""
        t = (time_of_day % 1)
        if t < 0.2 or t > 0.8:
            return 0.3  # Night
        elif t < 0.3 or t > 0.7:
            return 0.6  # Dawn/dusk
        else:
            return 1.0  # Day
    
    def draw_block(self, pos, block_type, camera_dist, light_level):
        x, y, z = pos
        color = BLOCK_DATA[block_type]["color"]
        
        # Apply lighting
        color = tuple(int(c * light_level) for c in color)
        
        # Projection
        screen_x = self.width // 2 + (x - z) * 15 - camera_dist * 2
        screen_y = self.height // 2 - y * 10 + camera_dist
        
        if 0 <= screen_x < self.width and 0 <= screen_y < self.height:
            size = max(2, 24 // (1 + camera_dist * 0.08))
            pygame.draw.rect(self.surface, color, 
                           (screen_x - size//2, screen_y - size//2, size, size))
            pygame.draw.rect(self.surface, (0, 0, 0), 
                           (screen_x - size//2, screen_y - size//2, size, size), 1)
    
    def draw_hud(self, player, world_time):
        """Draw HUD"""
        # Health
        health_text = f"❤ {int(player.health)}/20"
        text = font_medium.render(health_text, True, (255, 0, 0))
        self.surface.blit(text, (20, 20))
        
        # Hunger
        hunger_text = f"🍗 {int(player.hunger)}/20"
        text = font_medium.render(hunger_text, True, (255, 165, 0))
        self.surface.blit(text, (20, 60))
        
        # Time of day
        hour = int((world_time / DAY_LENGTH) * 24)
        minute = int(((world_time / DAY_LENGTH) * 24 - hour) * 60)
        time_text = f"Time: {hour:02d}:{minute:02d}"
        text = font_small.render(time_text, True, (200, 200, 200))
        self.surface.blit(text, (self.width - 250, 20))
        
        # Position
        pos_text = f"Pos: ({player.x:.1f}, {player.y:.1f}, {player.z:.1f})"
        text = font_small.render(pos_text, True, (200, 200, 200))
        self.surface.blit(text, (self.width - 400, 60))
        
        # Selected tool
        tool_names = {
            ToolType.HAND: "Hand",
            ToolType.WOODEN_PICKAXE: "Wooden Pickaxe",
            ToolType.STONE_PICKAXE: "Stone Pickaxe",
            ToolType.IRON_PICKAXE: "Iron Pickaxe",
        }
        tool_text = f"Tool: {tool_names[player.tool]}"
        text = font_small.render(tool_text, True, (200, 200, 200))
        self.surface.blit(text, (20, self.height - 60))
        
        # Hotbar
        hotbar_y = self.height - 80
        for i in range(5):
            x = 100 + i * 70
            color = (100, 150, 255) if i == player.selected_slot else (70, 70, 70)
            pygame.draw.rect(self.surface, color, (x, hotbar_y, 60, 60))
            pygame.draw.rect(self.surface, (200, 200, 200), (x, hotbar_y, 60, 60), 2)
            
            if player.hotbar[i] is not None:
                block = player.hotbar[i]
                block_name = BLOCK_DATA[block].get("name", "Unknown")[:4]
                count = player.inventory.get(block, 0)
                
                text = font_small.render(f"{block_name}", True, (255, 255, 255))
                self.surface.blit(text, (x + 5, hotbar_y + 5))
                text = font_small.render(f"{count}", True, (200, 200, 200))
                self.surface.blit(text, (x + 5, hotbar_y + 35))
        
        # Instructions
        instructions = [
            "WASD: Move | SPACE: Jump | LClick: Mine | RClick: Place",
            "E: Inventory | C: Craft | 1-5: Hotbar | ESC: Menu"
        ]
        for i, instr in enumerate(instructions):
            text = font_tiny.render(instr, True, (150, 150, 150))
            self.surface.blit(text, (20, self.height - 30 - i*20))
        
        # Crosshair
        cx, cy = self.width // 2, self.height // 2
        pygame.draw.line(self.surface, (255, 255, 255), (cx-12, cy), (cx+12, cy), 2)
        pygame.draw.line(self.surface, (255, 255, 255), (cx, cy-12), (cx, cy+12), 2)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy), 3, 1)
        
        # Mining progress
        if player.mining_block:
            progress_x = self.width // 2 - 50
            progress_y = self.height // 2 + 30
            pygame.draw.rect(self.surface, (50, 50, 50), (progress_x, progress_y, 100, 10))
            progress = min(1.0, player.mining_progress / 100)
            pygame.draw.rect(self.surface, (0, 255, 0), (progress_x, progress_y, 100 * progress, 10))

# ============= MAIN GAME =============
world = World()
player = Player()
renderer = Renderer(display[0], display[1])

running = True
world_time = 6000  # Start at dawn
last_break_click = 0
last_place_click = 0

while running:
    dt = clock.tick(60) / 1000.0
    world_time += dt
    
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if pygame.K_1 <= event.key <= pygame.K_5:
                player.selected_slot = event.key - pygame.K_1
            if event.key == pygame.K_e:
                pass  # TODO: Open inventory
            if event.key == pygame.K_c:
                pass  # TODO: Open crafting
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                last_break_click = pygame.time.get_ticks()
            if event.button == 3:
                last_place_click = pygame.time.get_ticks()
    
    # Continuous mining
    if pygame.time.get_ticks() - last_break_click < 1000:
        player.break_block(world, world_time)
    else:
        player.mining_block = None
        player.mining_progress = 0
    
    # Continuous placing
    if pygame.time.get_ticks() - last_place_click < 500:
        player.place_block(world)
        last_place_click = pygame.time.get_ticks() + 500
    
    # Mouse look
    mouse_x, mouse_y = pygame.mouse.get_rel()
    player.yaw -= mouse_x * 0.01
    player.pitch -= mouse_y * 0.01
    player.pitch = np.clip(player.pitch, -np.pi/2, np.pi/2)
    
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    
    # Update
    keys = pygame.key.get_pressed()
    player.update(keys, world, dt)
    
    # Update mobs
    for mob in world.mobs:
        mob.update(player, world)
    
    # Rendering
    sky_color = renderer.get_sky_color(world_time / DAY_LENGTH)
    light_level = renderer.get_block_light(world_time / DAY_LENGTH)
    
    renderer.clear(sky_color)
    
    # Draw world
    visible_blocks = world.get_visible_blocks(int(player.x), int(player.y), int(player.z), VIEW_DISTANCE)
    visible_blocks.sort(key=lambda b: (b[0][0]-player.x)**2 + (b[0][1]-player.y)**2 + (b[0][2]-player.z)**2, reverse=True)
    
    for (x, y, z), block_type in visible_blocks:
        dist = math.sqrt((x-player.x)**2 + (y-player.y)**2 + (z-player.z)**2)
        if dist < RENDER_DISTANCE:
            renderer.draw_block((x, y, z), block_type, dist, light_level)
    
    # Draw mobs
    for mob in world.mobs:
        mob_x = renderer.width // 2 + (mob.x - mob.z) * 15
        mob_y = renderer.height // 2 - mob.y * 10
        if 0 <= mob_x < renderer.width and 0 <= mob_y < renderer.height:
            pygame.draw.circle(renderer.surface, mob.color, (int(mob_x), int(mob_y)), 8)
    
    # Draw HUD
    renderer.draw_hud(player, world_time)
    
    # Display
    screen.blit(renderer.surface, (0, 0))
    
    # FPS counter
    fps_text = font_tiny.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
    screen.blit(fps_text, (display[0] - 100, 10))
    
    pygame.display.flip()

# Save world on exit
world.save()
pygame.quit()
