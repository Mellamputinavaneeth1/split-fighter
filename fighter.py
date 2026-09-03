"""
fighter.py -- Simple 1v1 arena fighter with jump, gravity, weapon system.
"""
import math

# --- Physics -----------------------------------------------------------------
GRAVITY       = 1200.0   # px/s
MOVE_SPEED    = 280.0
JUMP_SPEED    = -520.0
MAX_FALL      = 800.0
ARENA_LEFT    = 20
ARENA_RIGHT   = 1080

# --- Weapons -----------------------------------------------------------------
WEAPON_DEFS = {
    "fists":  {"name": "Fists",  "damage": 5,  "range": 55,  "cooldown": 0.35,
               "knockback": 120,  "block_mult": 0.5, "projectile": False},
    "sword":  {"name": "Sword",  "damage": 15, "range": 85,  "cooldown": 0.5,
               "knockback": 180,  "block_mult": 0.5, "projectile": False},
    "axe":    {"name": "Axe",    "damage": 22, "range": 65,  "cooldown": 0.85,
               "knockback": 280,  "block_mult": 0.5, "projectile": False},
    "shield": {"name": "Shield", "damage": 3,  "range": 40,  "cooldown": 0.6,
               "knockback": 60,   "block_mult": 0.8, "projectile": False},
    "bow":    {"name": "Bow",    "damage": 12, "range": 500, "cooldown": 1.0,
               "knockback": 80,   "block_mult": 0.5, "projectile": True},
}


class Fighter:
    WIDTH  = 36
    HEIGHT = 80

    def __init__(self, x: float, y: float, color: tuple, player_id: str, team="A"):
        self.x         = x
        self.y         = y
        self.color     = color
        self.player_id = player_id   # "P1" or "P2"
        self.team      = team

        # Physics
        self.vx        = 0.0
        self.vy        = 0.0
        self.on_ground = False
        self.facing    = 1   # 1 = right, -1 = left

        # Combat
        self.hp              = 100
        self.max_hp          = 100
        self.weapon          = "fists"    # current weapon key
        self.attack_timer    = 0.0        # cooldown remaining
        self.is_attacking    = False      # True during attack animation
        self.attack_anim     = 0.0        # attack animation timer (0..0.2s)
        self.blocking        = False
        self.hit_flash       = 0.0        # flash white on hit

        # Knockback
        self.kb_vx           = 0.0
        self.kb_timer        = 0.0

        # Stats
        self.damage_dealt    = 0
        self.kills           = 0

        # Coordination (4P mode)
        self.coord_bonus = 0.0    # seconds remaining of +15% damage
        self.coord_glow  = False  # visual flag for gold glow

    # -- Properties ------------------------------------------------------------
    @property
    def rect(self):
        return (self.x, self.y, self.WIDTH, self.HEIGHT)

    @property
    def center_x(self):
        return self.x + self.WIDTH / 2

    @property
    def center_y(self):
        return self.y + self.HEIGHT / 2

    @property
    def weapon_info(self) -> dict:
        return WEAPON_DEFS.get(self.weapon, WEAPON_DEFS["fists"])

    @property
    def alive(self) -> bool:
        return self.hp > 0

    # -- Actions ---------------------------------------------------------------
    def move(self, direction: int):
        """direction: -1 (left), 0 (stop), 1 (right)"""
        self.vx = direction * MOVE_SPEED
        if direction != 0:
            self.facing = direction

    def move_input(self, direction: int):
        """Mover role: set velocity WITHOUT changing facing direction."""
        self.vx = direction * MOVE_SPEED

    def face_input(self, direction: int):
        """Attacker role: change facing direction WITHOUT moving."""
        if direction != 0:
            self.facing = direction

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

    def attack(self) -> bool:
        """Try to attack. Returns True if attack started."""
        if self.attack_timer > 0:
            return False
        info = self.weapon_info
        self.attack_timer = info["cooldown"]
        self.is_attacking = True
        self.attack_anim  = 0.2   # animation lasts 0.2s
        return True

    def start_block(self):
        self.blocking = True

    def stop_block(self):
        self.blocking = False

    def take_damage(self, dmg: int, direction: int, knockback: float):
        """Apply damage and knockback."""
        # Blocking reduces damage
        if self.blocking:
            mult = WEAPON_DEFS.get(self.weapon, WEAPON_DEFS["fists"])["block_mult"]
            dmg = max(1, int(dmg * (1.0 - mult)))
            knockback *= 0.3

        self.hp -= dmg
        self.hit_flash = 0.25
        self.kb_vx     = direction * knockback * 3
        self.kb_timer  = 0.15

    def pickup_weapon(self, weapon_key: str):
        self.weapon = weapon_key

    def drop_weapon(self) -> str | None:
        if self.weapon != "fists":
            old = self.weapon
            self.weapon = "fists"
            return old
        return None

    # -- Update ----------------------------------------------------------------
    def update(self, dt: float, platforms: list, walls: list):
        """Update physics, timers, collisions."""
        # Timers
        if self.attack_timer > 0:
            self.attack_timer = max(0, self.attack_timer - dt)
        if self.attack_anim > 0:
            self.attack_anim = max(0, self.attack_anim - dt)
            if self.attack_anim <= 0:
                self.is_attacking = False
        if self.hit_flash > 0:
            self.hit_flash = max(0, self.hit_flash - dt)
        if self.coord_bonus > 0:
            self.coord_bonus = max(0, self.coord_bonus - dt)
            self.coord_glow = self.coord_bonus > 0

        # Knockback
        if self.kb_timer > 0:
            self.kb_timer -= dt
            self.x += self.kb_vx * dt
        else:
            self.kb_vx = 0

        # Gravity
        self.vy += GRAVITY * dt
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        # Move X
        new_x = self.x + (self.vx + self.kb_vx * 0.5) * dt
        # Wall collisions X
        new_x = self._collide_x(new_x, walls)
        # Arena bounds
        new_x = max(ARENA_LEFT, min(ARENA_RIGHT - self.WIDTH, new_x))
        self.x = new_x

        # Move Y
        new_y = self.y + self.vy * dt
        self.on_ground = False

        # Platform / ground collisions Y
        new_y, landed = self._collide_y(new_y, platforms + walls)
        if landed:
            self.vy = 0
            self.on_ground = True

        self.y = new_y

    def _collide_x(self, new_x: float, walls: list) -> float:
        """Check horizontal collision with walls."""
        my_top    = self.y
        my_bottom = self.y + self.HEIGHT
        for w in walls:
            wx, wy, ww, wh = w["x"], w["y"], w["w"], w["h"]
            # Does this wall overlap vertically with me?
            if my_bottom > wy + 2 and my_top < wy + wh - 2:
                # Moving right into left side of wall
                if new_x + self.WIDTH > wx and self.x + self.WIDTH <= wx + 2:
                    new_x = wx - self.WIDTH
                # Moving left into right side of wall
                elif new_x < wx + ww and self.x >= wx + ww - 2:
                    new_x = wx + ww
        return new_x

    def _collide_y(self, new_y: float, surfaces: list) -> tuple:
        """Check vertical collision. Returns (new_y, landed)."""
        my_left  = self.x + 4
        my_right = self.x + self.WIDTH - 4

        for s in surfaces:
            sx, sy, sw, sh = s["x"], s["y"], s["w"], s["h"]
            # Only land on top of surfaces (falling down)
            if self.vy >= 0:
                # Are we horizontally overlapping?
                if my_right > sx and my_left < sx + sw:
                    # Were we above the surface, now passing through?
                    if self.y + self.HEIGHT <= sy + 4 and new_y + self.HEIGHT >= sy:
                        return sy - self.HEIGHT, True
        return new_y, False

    def reset(self, x: float, y: float):
        self.x = x; self.y = y
        self.vx = 0; self.vy = 0
        self.hp = self.max_hp
        self.weapon = "fists"
        self.attack_timer = 0; self.is_attacking = False
        self.attack_anim = 0; self.blocking = False
        self.hit_flash = 0; self.kb_vx = 0; self.kb_timer = 0
        self.on_ground = False
        self.damage_dealt = 0
        self.coord_bonus = 0.0
        self.coord_glow = False

    # -- Serialization (for Firebase) ------------------------------------------
    def to_dict(self) -> dict:
        return {
            "x": round(self.x, 1), "y": round(self.y, 1),
            "vx": round(self.vx, 1), "vy": round(self.vy, 1),
            "hp": self.hp, "weapon": self.weapon,
            "facing": self.facing, "on_ground": self.on_ground,
            "attacking": self.is_attacking, "attack_anim": round(self.attack_anim, 3),
            "blocking": self.blocking, "hit_flash": round(self.hit_flash, 3),
            "damage_dealt": self.damage_dealt,
            "team": self.team,
            "coord_bonus": round(self.coord_bonus, 2),
        }

    def from_dict(self, d: dict):
        if not d: return
        self.x           = d.get("x", self.x)
        self.y           = d.get("y", self.y)
        self.vx          = d.get("vx", self.vx)
        self.vy          = d.get("vy", self.vy)
        self.hp          = d.get("hp", self.hp)
        self.weapon      = d.get("weapon", self.weapon)
        self.facing      = d.get("facing", self.facing)
        self.on_ground   = d.get("on_ground", self.on_ground)
        self.is_attacking = d.get("attacking", self.is_attacking)
        self.attack_anim = d.get("attack_anim", self.attack_anim)
        self.blocking    = d.get("blocking", self.blocking)
        self.hit_flash   = d.get("hit_flash", self.hit_flash)
        self.damage_dealt = d.get("damage_dealt", self.damage_dealt)
        self.team = d.get("team", self.team)
        self.coord_bonus = d.get("coord_bonus", self.coord_bonus)
        self.coord_glow = self.coord_bonus > 0
