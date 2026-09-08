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
        bob = math.sin(t * 3.5 + self.x * 0.1) * 5
        vis = WEAPON_VISUALS.get(self.weapon, {})
        col = vis.get("color", (200, 200, 200))
        glow_col = vis.get("glow", col)

        cx = int(self.x + self.SIZE // 2)
        cy = int(self.y + self.SIZE // 2 + bob)

        # Holographic Light Pedestal on Ground / Platform
        ped_y = int(self.y + self.SIZE + 4)
        ped = pygame.Surface((44, 12), pygame.SRCALPHA)
        ped_alpha = int(45 + 25 * math.sin(t * 4))
        pygame.draw.ellipse(ped, (*glow_col, ped_alpha), (0, 0, 44, 12))
        surface.blit(ped, (cx - 22, ped_y - 6))

        # Ambient Glow Bubble
        glow = pygame.Surface((56, 56), pygame.SRCALPHA)
        p = int(40 + 25 * math.sin(t * 4))
        pygame.draw.circle(glow, (*glow_col, p), (28, 28), 24)
        surface.blit(glow, (cx - 28, cy - 28))

        # Vector Weapon Models
        if self.weapon == "sword":
            # Double-edged steel blade with gleam
            pygame.draw.polygon(surface, (235, 242, 255),
                                [(cx, cy - 18), (cx + 4, cy - 12), (cx + 3, cy + 6),
                                 (cx, cy + 8), (cx - 3, cy + 6), (cx - 4, cy - 12)])
            pygame.draw.line(surface, (255, 255, 255), (cx, cy - 17), (cx, cy + 7), 1)
            # Golden crossguard
            pygame.draw.rect(surface, (250, 200, 50), (cx - 8, cy + 7, 16, 3), border_radius=1)
            pygame.draw.circle(surface, (255, 230, 90), (cx - 8, cy + 8), 2)
            pygame.draw.circle(surface, (255, 230, 90), (cx + 8, cy + 8), 2)
            # Wrapped hilt & pommel
            pygame.draw.rect(surface, (110, 55, 20), (cx - 2, cy + 10, 4, 6), border_radius=1)
            pygame.draw.circle(surface, (250, 200, 50), (cx, cy + 17), 3)

        elif self.weapon == "axe":
            # Wooden haft
            pygame.draw.rect(surface, (130, 75, 30), (cx - 2, cy - 18, 4, 36), border_radius=1)
            # Dual curved iron axe heads
            pygame.draw.polygon(surface, (180, 195, 215),
                                [(cx + 2, cy - 14), (cx + 14, cy - 18), (cx + 16, cy - 6),
                                 (cx + 10, cy + 2), (cx + 2, cy - 2)])
            pygame.draw.polygon(surface, (180, 195, 215),
                                [(cx - 2, cy - 14), (cx - 14, cy - 18), (cx - 16, cy - 6),
                                 (cx - 10, cy + 2), (cx - 2, cy - 2)])
            # Silver blade edge highlights
            pygame.draw.lines(surface, (255, 255, 255), False,
                              [(cx + 14, cy - 18), (cx + 16, cy - 6), (cx + 10, cy + 2)], 2)
            pygame.draw.lines(surface, (255, 255, 255), False,
                              [(cx - 14, cy - 18), (cx - 16, cy - 6), (cx - 10, cy + 2)], 2)
            # Center bracket & rivet
            pygame.draw.rect(surface, (70, 80, 100), (cx - 3, cy - 11, 6, 7), border_radius=1)
            pygame.draw.circle(surface, (255, 215, 0), (cx, cy - 8), 2)

        elif self.weapon == "bow":
            # Curved wooden stave
            pygame.draw.arc(surface, (180, 110, 40), (cx - 13, cy - 18, 26, 36),
                            math.pi * 0.25, math.pi * 1.75, 4)
            pygame.draw.arc(surface, (240, 160, 60), (cx - 13, cy - 18, 26, 36),
                            math.pi * 0.25, math.pi * 1.75, 2)
            # Taut bowstring
            pygame.draw.line(surface, (240, 240, 255), (cx - 4, cy - 16), (cx - 4, cy + 16), 1)
            # Arrow nocked in center
            pygame.draw.line(surface, (150, 90, 30), (cx - 8, cy), (cx + 12, cy), 2)
            pygame.draw.polygon(surface, (230, 240, 255), [(cx + 12, cy - 3), (cx + 18, cy), (cx + 12, cy + 3)])
            pygame.draw.line(surface, (230, 50, 50), (cx - 7, cy - 2), (cx - 5, cy), 1)
            pygame.draw.line(surface, (230, 50, 50), (cx - 7, cy + 2), (cx - 5, cy), 1)

        elif self.weapon == "shield":
            # Kite shield body
            shield_pts = [(cx, cy - 18), (cx + 13, cy - 12), (cx + 11, cy + 6),
                          (cx, cy + 18), (cx - 11, cy + 6), (cx - 13, cy - 12)]
            pygame.draw.polygon(surface, (30, 50, 90), shield_pts)
            pygame.draw.polygon(surface, (190, 210, 245), shield_pts, 2)
            # Golden cross & boss
            pygame.draw.line(surface, (255, 215, 0), (cx, cy - 12), (cx, cy + 12), 2)
            pygame.draw.line(surface, (255, 215, 0), (cx - 8, cy - 3), (cx + 8, cy - 3), 2)
            pygame.draw.circle(surface, (255, 230, 90), (cx, cy - 3), 3)

        # Sleek Floating Label Pill
        label = font.render(self.weapon.upper(), True, col)
        lw, lh = label.get_width() + 10, label.get_height() + 2
        lx = cx - lw // 2
        ly = cy - 28
        lb_bg = pygame.Surface((lw, lh), pygame.SRCALPHA)
        lb_bg.fill((16, 18, 30, 200))
        surface.blit(lb_bg, (lx, ly))
        pygame.draw.rect(surface, (60, 70, 95), (lx, ly, lw, lh), 1, border_radius=4)
        surface.blit(label, (cx - label.get_width() // 2, ly + 1))


# --- Arrow projectile --------------------------------------------------------
class Arrow:
    SPEED = 650.0

    def __init__(self, x, y, direction, owner_id, owner_team="A"):
        self.x = x
        self.y = y
        self.vx = direction * self.SPEED
        self.direction = direction
        self.owner_id = owner_id
        self.owner_team = owner_team
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
        if not self.alive or fighter.player_id == self.owner_id or (hasattr(fighter, 'team') and fighter.team == self.owner_team):
            return False
        fx, fy, fw, fh = fighter.rect
        return (self.x > fx and self.x < fx + fw and
                self.y > fy and self.y < fy + fh)

    def to_dict(self):
        return {"x": round(self.x, 1), "y": round(self.y, 1),
                "vx": round(self.vx, 1), "owner": self.owner_id, "team": self.owner_team}

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

        # Cyberpunk City Skyline silhouette (background depth)
        self.skyline = []
        cur_x = 0
        while cur_x < width + 120:
            bw = random.randint(45, 95)
            bh = random.randint(110, 260)
            windows = []
            for wy in range(GROUND_Y - bh + 16, GROUND_Y - 25, 18):
                for wx in range(cur_x + 8, cur_x + bw - 10, 14):
                    if random.random() < 0.6:
                        windows.append((wx, wy))
            has_beacon = random.random() < 0.45
            self.skyline.append({
                "x": cur_x, "w": bw, "h": bh,
                "windows": windows,
                "beacon": has_beacon,
            })
            cur_x += bw + random.randint(6, 18)

    def update(self, dt):
        for wp in self.weapon_pickups:
            wp.update(dt)
        for a in self.arrows:
            a.update(dt, self.walls + self.platforms)
        self.arrows[:] = [a for a in self.arrows if a.alive]

    def spawn_arrow(self, x, y, direction, owner_id, owner_team="A"):
        self.arrows.append(Arrow(x, y, direction, owner_id, owner_team))

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
        # 1. Atmospheric Deep Night Sky
        surface.fill((12, 14, 26))
        t = _time.time()

        # Stars (twinkling)
        for s in self.stars:
            pulse = 0.5 + 0.5 * math.sin(t * s["speed"] * 0.3 + s["x"] * 0.01)
            a = int(s["a"] * pulse)
            pygame.draw.circle(surface, (a, a, min(255, int(a * 1.35))),
                               (int(s["x"] + cam_x * 0.08), int(s["y"] + cam_y * 0.08)),
                               max(1, int(s["r"])))

        # 2. Cyberpunk City Skyline in distance
        for b in getattr(self, "skyline", []):
            bx = int(b["x"] + cam_x * 0.15)
            by = GROUND_Y - b["h"]
            bw, bh = b["w"], b["h"]
            # Dark skyscraper silhouette
            pygame.draw.rect(surface, (18, 22, 36), (bx, by, bw, bh))
            pygame.draw.rect(surface, (28, 34, 52), (bx, by, bw, bh), 1)

            # Glowing windows
            for wx, wy in b["windows"]:
                wx_screen = int(wx + cam_x * 0.15)
                # Subtle window shimmer
                w_shimmer = 0.6 + 0.4 * math.sin(t * 1.5 + wx * 0.2)
                w_col = (int(50 * w_shimmer), int(75 * w_shimmer), int(120 * w_shimmer))
                pygame.draw.rect(surface, w_col, (wx_screen, wy, 4, 6))

            # Rooftop beacon light
            if b.get("beacon"):
                beacon_alpha = int(140 + 115 * math.sin(t * 5 + b["x"]))
                pygame.draw.circle(surface, (beacon_alpha, 40, 40), (bx + bw // 2, by - 4), 2)
                pygame.draw.line(surface, (45, 52, 75), (bx + bw // 2, by), (bx + bw // 2, by - 4), 1)

        # 3. High-Tech Ground Floor
        ground = self.platforms[0]
        gx, gy = int(ground["x"] + cam_x), int(ground["y"] + cam_y)
        gw, gh = ground["w"], ground["h"]

        # Base steel plate
        pygame.draw.rect(surface, (26, 28, 42), (gx, gy, gw, gh))

        # Top 8px Hazard Caution Stripes (///)
        hazard_h = 8
        pygame.draw.rect(surface, (20, 22, 34), (gx, gy, gw, hazard_h))
        stripe_w = 18
        for sx in range(gx - 20, gx + gw + 20, stripe_w):
            pts = [(sx, gy + hazard_h), (sx + 8, gy + hazard_h),
                   (sx + 14, gy), (sx + 6, gy)]
            pygame.draw.polygon(surface, (200, 150, 45), pts)

        # Neon Cyan Boundary Line
        pygame.draw.line(surface, (56, 189, 248), (gx, gy), (gx + gw, gy), 2)

        # Steel panel vertical joints & rivets
        for px in range(gx + 50, gx + gw, 60):
            pygame.draw.line(surface, (18, 20, 32), (px, gy + hazard_h), (px, gy + gh), 1)
            pygame.draw.circle(surface, (70, 80, 105), (px, gy + hazard_h + 8), 1.5)

        # 4. Sci-Fi Floating Platforms (skip ground at index 0)
        for p in self.platforms[1:]:
            px, py = int(p["x"] + cam_x), int(p["y"] + cam_y)
            pw, ph = p["w"], p["h"]

            # Dark tech chassis
            pygame.draw.rect(surface, (34, 40, 58), (px, py, pw, ph), border_radius=3)
            pygame.draw.rect(surface, (50, 58, 82), (px, py, pw, ph), 1, border_radius=3)

            # Metal vent grating in center
            for vx in range(px + 16, px + pw - 16, 12):
                pygame.draw.line(surface, (22, 26, 40), (vx, py + 4), (vx, py + ph - 4), 2)

            # Top walking edge with glowing cyan sheen
            pygame.draw.line(surface, (56, 189, 248), (px + 1, py), (px + pw - 1, py), 2)
            pygame.draw.line(surface, (186, 230, 253), (px + 3, py), (px + pw - 3, py), 1)

            # Neon Thruster Nodes underneath
            t1_x = px + int(pw * 0.22)
            t2_x = px + int(pw * 0.78)
            for tx in (t1_x, t2_x):
                # Thruster nozzle
                pygame.draw.rect(surface, (25, 28, 42), (tx - 5, py + ph, 10, 3))
                # Soft downward cyan thruster light
                thruster_alpha = int(70 + 40 * math.sin(t * 6 + px))
                glow_s = pygame.Surface((18, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(glow_s, (56, 189, 248, thruster_alpha), (0, 0, 18, 12))
                surface.blit(glow_s, (tx - 9, py + ph))

        # 5. Obstacles: Military Cargo Crates & Stone Monoliths
        for w in self.walls:
            if w.get("hp", 1) <= 0:
                continue
            wx, wy = int(w["x"] + cam_x), int(w["y"] + cam_y)
            ww, wh = w["w"], w["h"]

            if w.get("destructible"):
                # Military Cargo Crate
                hp_ratio = w["hp"] / w["max_hp"] if w["max_hp"] > 0 else 1.0

                # Base wooden box
                pygame.draw.rect(surface, (120, 72, 32), (wx, wy, ww, wh), border_radius=2)

                # Horizontal plank lines
                pygame.draw.line(surface, (75, 42, 16), (wx, wy + wh // 3), (wx + ww, wy + wh // 3), 1)
                pygame.draw.line(surface, (75, 42, 16), (wx, wy + (wh * 2) // 3), (wx + ww, wy + (wh * 2) // 3), 1)

                # Diagonal reinforcement beams
                pygame.draw.line(surface, (145, 88, 38), (wx + 4, wy + 4), (wx + ww - 4, wy + wh - 4), 2)
                pygame.draw.line(surface, (145, 88, 38), (wx + ww - 4, wy + 4), (wx + 4, wy + wh - 4), 2)

                # Reinforced Iron Corner Brackets
                corner_sz = min(8, ww // 3)
                for cx3, cy3 in [(wx, wy), (wx + ww - corner_sz, wy),
                                 (wx, wy + wh - corner_sz), (wx + ww - corner_sz, wy + wh - corner_sz)]:
                    pygame.draw.rect(surface, (90, 102, 122), (cx3, cy3, corner_sz, corner_sz))
                    pygame.draw.circle(surface, (255, 215, 0), (cx3 + corner_sz // 2, cy3 + corner_sz // 2), 1.5)

                pygame.draw.rect(surface, (60, 35, 15), (wx, wy, ww, wh), 1, border_radius=2)

                # Damage Fractures & HP Bar
                if hp_ratio < 1.0:
                    # Jagged crack lines
                    pygame.draw.line(surface, (250, 160, 40), (wx + 6, wy + 8), (wx + ww // 2, wy + wh // 2), 1)
                    pygame.draw.line(surface, (250, 160, 40), (wx + ww // 2, wy + wh // 2), (wx + ww - 8, wy + wh - 6), 1)

                    # Floating micro HP bar
                    bar_w3 = ww
                    pygame.draw.rect(surface, (20, 22, 34), (wx, wy - 7, bar_w3, 4), border_radius=1)
                    pygame.draw.rect(surface, (235, 75, 45), (wx, wy - 7, int(bar_w3 * hp_ratio), 4), border_radius=1)

            else:
                # Stone Pillar / Ancient Monolith
                pygame.draw.rect(surface, (55, 60, 72), (wx, wy, ww, wh))
                pygame.draw.rect(surface, (80, 88, 105), (wx, wy, ww, 3))  # top highlight bevel

                # Chiseled Brick courses
                course_h = 14
                for row_y in range(0, wh, course_h):
                    pygame.draw.line(surface, (35, 38, 48), (wx, wy + row_y), (wx + ww, wy + row_y), 1)
                    off = (ww // 2) if ((row_y // course_h) % 2 == 1) else 0
                    pygame.draw.line(surface, (35, 38, 48), (wx + off, wy + row_y), (wx + off, wy + min(wh, row_y + course_h)), 1)

                pygame.draw.rect(surface, (32, 35, 45), (wx, wy, ww, wh), 2)

        # 6. High-Detail Weapon Pickups
        for wp in self.weapon_pickups:
            wp.draw(surface, font_small)

        # 7. Arrows
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
