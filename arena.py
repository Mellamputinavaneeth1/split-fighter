"""
arena.py -- Map definition with platforms, walls, crates, weapon spawns.
"""
import pygame
import math
import random
import time as _time


# --- Map elements -------------------------------------------------------------
GROUND_Y = 555
GROUND_H = 145   # thickness of ground bar

# Colors
C_GROUND   = (35, 35, 50)
C_GROUND_TOP = (55, 55, 80)
C_PLATFORM = (50, 50, 70)
C_PLAT_TOP = (80, 80, 110)
C_WALL     = (70, 60, 55)
C_WALL_DARK= (50, 42, 38)
C_CRATE    = (140, 100, 50)
C_CRATE_DK = (100, 70, 35)
C_BG       = (12, 12, 22)

# --- Weapon pickup colors/icons ----------------------------------------------
WEAPON_VISUALS = {
    "sword":  {"color": (180, 200, 220), "icon": "SWORD", "glow": (120, 150, 255)},
    "axe":    {"color": (200, 140, 80),  "icon": "AXE", "glow": (255, 140, 50)},
    "shield": {"color": (100, 160, 220), "icon": "SHIELD", "glow": (80, 160, 255)},
    "bow":    {"color": (160, 200, 120), "icon": "BOW", "glow": (120, 255, 80)},
}


# --- Platform / Wall dicts ---------------------------------------------------
def _plat(x, y, w, h=16):
    return {"x": x, "y": y, "w": w, "h": h, "type": "platform"}

def _wall(x, y, w, h, destructible=False, hp=30):
    return {"x": x, "y": y, "w": w, "h": h, "type": "wall",
            "destructible": destructible, "hp": hp, "max_hp": hp}

def _ground():
    return {"x": 0, "y": GROUND_Y, "w": 1100, "h": GROUND_H, "type": "ground"}


# --- Map layout --------------------------------------------------------------
def create_map():
    """Returns (platforms, walls, weapon_spawns)."""
    platforms = [
        _ground(),
        # Left floating platform
        _plat(100, 400, 220),
        # Right floating platform
        _plat(780, 400, 220),
        # Center high platform
        _plat(400, 280, 300),
        # Small step platforms
        _plat(50,  490, 100),
        _plat(950, 490, 100),
    ]

    walls = [
        # Left ground pillar
        _wall(300, 480, 30, 75),
        # Right ground pillar
        _wall(770, 480, 30, 75),
        # Center ground pillar
        _wall(535, 430, 30, 125),
        # Crate on left platform (destructible)
        _wall(180, 368, 32, 32, destructible=True, hp=25),
        # Crate on right platform (destructible)
        _wall(880, 368, 32, 32, destructible=True, hp=25),
        # Crate on ground center
        _wall(520, 523, 32, 32, destructible=True, hp=25),
    ]

    weapon_spawns = [
        {"x": 520, "y": 248, "weapon": "sword"},    # center high platform
        {"x": 160, "y": 523, "weapon": "axe"},       # ground left
        {"x": 900, "y": 523, "weapon": "shield"},    # ground right
        {"x": 160, "y": 368, "weapon": "bow"},       # left platform
    ]

    return platforms, walls, weapon_spawns


# --- Weapon Pickup -----------------------------------------------------------
class WeaponPickup:
    RESPAWN_TIME = 15.0
    SIZE = 28

    def __init__(self, x, y, weapon_type):
        self.spawn_x = x
        self.spawn_y = y
        self.x = x
        self.y = y
        self.weapon = weapon_type
        self.active = True
        self.respawn_timer = 0.0

    def update(self, dt):
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True
                self.x = self.spawn_x
                self.y = self.spawn_y

    def collect(self):
        self.active = False
        self.respawn_timer = self.RESPAWN_TIME

    def collides_with(self, fighter) -> bool:
        if not self.active:
            return False
        fx, fy, fw, fh = fighter.rect
        return (fx + fw > self.x and fx < self.x + self.SIZE and
                fy + fh > self.y and fy < self.y + self.SIZE)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "weapon": self.weapon,
                "active": self.active, "respawn": round(self.respawn_timer, 2)}

    def from_dict(self, d):
        if not d: return
        self.active = d.get("active", self.active)
        self.respawn_timer = d.get("respawn", self.respawn_timer)

    def draw(self, surface, font):
        if not self.active:
            return
        t = _time.time()
        bob = math.sin(t * 3 + self.x * 0.1) * 4
        vis = WEAPON_VISUALS.get(self.weapon, {})
        col = vis.get("color", (200, 200, 200))
        glow_col = vis.get("glow", col)

        dx, dy = int(self.x), int(self.y + bob)

        # Glow
        glow = pygame.Surface((48, 48), pygame.SRCALPHA)
        p = int(40 + 30 * math.sin(t * 4))
        pygame.draw.ellipse(glow, (*glow_col, p), (0, 0, 48, 48))
        surface.blit(glow, (dx - 10, dy - 10))

        # Item box
        pygame.draw.rect(surface, col, (dx, dy, self.SIZE, self.SIZE), border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), (dx, dy, self.SIZE, self.SIZE), 1, border_radius=4)

        # Label
        label = font.render(self.weapon.upper(), True, col)
        surface.blit(label, (dx + self.SIZE // 2 - label.get_width() // 2, dy - 14))


# --- Arrow projectile --------------------------------------------------------
class Arrow:
    SPEED = 650.0

    def __init__(self, x, y, direction, owner_id):
        self.x = x
        self.y = y
        self.vx = direction * self.SPEED
        self.direction = direction
        self.owner_id = owner_id
        self.alive = True
        self.damage = 12
        self.knockback = 80

    def update(self, dt, walls):
        self.x += self.vx * dt
        # Check wall collisions
        for w in walls:
            wx, wy, ww, wh = w["x"], w["y"], w["w"], w["h"]
            if (self.x > wx and self.x < wx + ww and
                self.y > wy and self.y < wy + wh):
                self.alive = False
                return
        # Out of bounds
        if self.x < 0 or self.x > 1100:
            self.alive = False

    def hits_fighter(self, fighter) -> bool:
        if not self.alive or fighter.player_id == self.owner_id:
            return False
        fx, fy, fw, fh = fighter.rect
        return (self.x > fx and self.x < fx + fw and
                self.y > fy and self.y < fy + fh)

    def to_dict(self):
        return {"x": round(self.x, 1), "y": round(self.y, 1),
                "vx": round(self.vx, 1), "owner": self.owner_id}

    def draw(self, surface):
        if not self.alive:
            return
        # Arrow body
        ex = int(self.x)
        ey = int(self.y)
        tail_x = ex - self.direction * 18
        pygame.draw.line(surface, (220, 200, 140), (tail_x, ey), (ex, ey), 3)
        # Arrowhead
        pygame.draw.polygon(surface, (255, 80, 50), [
            (ex + self.direction * 6, ey),
            (ex, ey - 4), (ex, ey + 4)])


# --- Arena renderer ----------------------------------------------------------
class Arena:
    def __init__(self, width, height):
        self.W = width
        self.H = height
        self.platforms, self.walls, weapon_spawn_data = create_map()
        self.weapon_pickups = [
            WeaponPickup(s["x"], s["y"], s["weapon"]) for s in weapon_spawn_data
        ]
        self.arrows: list[Arrow] = []

        # Background stars
        self.stars = [
            {"x": random.randint(0, width), "y": random.randint(0, height - 200),
             "r": random.uniform(0.8, 2.5), "speed": random.uniform(3, 12),
             "a": random.randint(40, 140)}
            for _ in range(80)
        ]

    def update(self, dt):
        for wp in self.weapon_pickups:
            wp.update(dt)
        for a in self.arrows:
            a.update(dt, self.walls + self.platforms)
        self.arrows[:] = [a for a in self.arrows if a.alive]

    def spawn_arrow(self, x, y, direction, owner_id):
        self.arrows.append(Arrow(x, y, direction, owner_id))

    def get_collide_surfaces(self):
        """Return all surfaces fighters can stand on."""
        return self.platforms + [w for w in self.walls if w.get("hp", 1) > 0]

    def get_walls_only(self):
        """Return just the walls (for X collision)."""
        return [w for w in self.walls if w.get("hp", 1) > 0]

    def damage_wall(self, wall, dmg):
        if wall.get("destructible"):
            wall["hp"] = max(0, wall["hp"] - dmg)

    def reset(self):
        _, self.walls, _ = create_map()
        for wp in self.weapon_pickups:
            wp.active = True
            wp.respawn_timer = 0
            wp.x = wp.spawn_x
            wp.y = wp.spawn_y
        self.arrows.clear()

    # -- Drawing --------------------------------------------------------------
    def draw(self, surface, font_small, cam_x=0, cam_y=0):
        # Background
        surface.fill(C_BG)
        t = _time.time()
        for s in self.stars:
            pulse = 0.5 + 0.5 * math.sin(t * s["speed"] * 0.3 + s["x"] * 0.01)
            a = int(s["a"] * pulse)
            pygame.draw.circle(surface, (a, a, min(255, int(a * 1.4))),
                               (int(s["x"] + cam_x * 0.1), int(s["y"] + cam_y * 0.1)),
                               max(1, int(s["r"])))

        # Ground
        ground = self.platforms[0]
        gx, gy = int(ground["x"] + cam_x), int(ground["y"] + cam_y)
        pygame.draw.rect(surface, C_GROUND, (gx, gy, ground["w"], ground["h"]))
        pygame.draw.line(surface, C_GROUND_TOP, (gx, gy), (gx + ground["w"], gy), 3)
        # Ground grid lines
        for i in range(0, ground["w"], 40):
            pygame.draw.line(surface, (25, 25, 40), (gx + i, gy + 4), (gx + i, gy + ground["h"]), 1)

        # Platforms (skip ground at index 0)
        for p in self.platforms[1:]:
            px, py = int(p["x"] + cam_x), int(p["y"] + cam_y)
            pw, ph = p["w"], p["h"]
            pygame.draw.rect(surface, C_PLATFORM, (px, py, pw, ph), border_radius=3)
            pygame.draw.line(surface, C_PLAT_TOP, (px + 2, py), (px + pw - 2, py), 3)
            # Underside shadow
            pygame.draw.line(surface, (30, 30, 45), (px + 4, py + ph), (px + pw - 4, py + ph), 2)

        # Walls
        for w in self.walls:
            if w.get("hp", 1) <= 0:
                continue
            wx, wy = int(w["x"] + cam_x), int(w["y"] + cam_y)
            ww, wh = w["w"], w["h"]
            if w.get("destructible"):
                # Crate style
                hp_ratio = w["hp"] / w["max_hp"] if w["max_hp"] > 0 else 1
                c = (int(C_CRATE[0] * hp_ratio), int(C_CRATE[1] * hp_ratio), int(C_CRATE[2] * hp_ratio))
                pygame.draw.rect(surface, c, (wx, wy, ww, wh), border_radius=2)
                pygame.draw.line(surface, C_CRATE_DK, (wx, wy), (wx + ww, wy + wh), 1)
                pygame.draw.line(surface, C_CRATE_DK, (wx + ww, wy), (wx, wy + wh), 1)
                pygame.draw.rect(surface, C_CRATE_DK, (wx, wy, ww, wh), 2, border_radius=2)
                # HP indicator
                if hp_ratio < 1.0:
                    bw = ww - 4
                    pygame.draw.rect(surface, (80, 20, 20), (wx + 2, wy - 6, bw, 4), border_radius=1)
                    pygame.draw.rect(surface, (220, 80, 40), (wx + 2, wy - 6, int(bw * hp_ratio), 4), border_radius=1)
            else:
                # Stone wall
                pygame.draw.rect(surface, C_WALL, (wx, wy, ww, wh))
                # Brick pattern
                for by in range(0, wh, 12):
                    off = 6 if (by // 12) % 2 == 1 else 0
                    for bx in range(off, ww, 12):
                        pygame.draw.rect(surface, C_WALL_DARK,
                                         (wx + bx, wy + by, min(11, ww - bx), 11), 1)
                pygame.draw.rect(surface, C_WALL_DARK, (wx, wy, ww, wh), 2)

        # Weapon pickups
        for wp in self.weapon_pickups:
            wp.draw(surface, font_small)

        # Arrows
        for a in self.arrows:
            a.draw(surface)

    # -- Serialization --------------------------------------------------------
    def to_dict(self):
        return {
            "weapons": [wp.to_dict() for wp in self.weapon_pickups],
            "arrows":  [a.to_dict() for a in self.arrows if a.alive],
            "walls":   [{"hp": w["hp"]} for w in self.walls if w.get("destructible")],
        }

    def from_dict(self, d):
        if not d: return
        for i, wd in enumerate(d.get("weapons", [])):
            if i < len(self.weapon_pickups):
                self.weapon_pickups[i].from_dict(wd)
        # Destructible wall HP
        dest_walls = [w for w in self.walls if w.get("destructible")]
        for i, wd in enumerate(d.get("walls", [])):
            if i < len(dest_walls):
                dest_walls[i]["hp"] = wd.get("hp", dest_walls[i]["hp"])
