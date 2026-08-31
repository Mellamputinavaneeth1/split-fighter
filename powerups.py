import pygame
import random
import math

# ─── Power-Up Types ──────────────────────────────────────────────────────────
POWERUP_HEALTH     = "health"
POWERUP_STAMINA    = "stamina"
POWERUP_DAMAGE     = "damage_boost"
POWERUP_SPEED      = "speed_boost"
POWERUP_SHIELD     = "shield"
POWERUP_SWORD      = "sword"
POWERUP_FIRE_FIST  = "fire_fist"

POWERUP_DEFS = {
    POWERUP_HEALTH:    {"name": "Health Pack",    "color": (50, 220, 80),   "icon": "+",  "duration": 0,   "desc": "Restore 25 HP"},
    POWERUP_STAMINA:   {"name": "Energy Drink",   "color": (240, 200, 40),  "icon": "E",  "duration": 0,   "desc": "Restore 40 Stamina"},
    POWERUP_DAMAGE:    {"name": "Damage Boost",   "color": (255, 80, 80),   "icon": "D",  "duration": 8.0, "desc": "2x Damage for 8s"},
    POWERUP_SPEED:     {"name": "Speed Boost",    "color": (80, 255, 200),  "icon": "S",  "duration": 6.0, "desc": "1.5x Speed for 6s"},
    POWERUP_SHIELD:    {"name": "Shield",          "color": (100, 150, 255), "icon": "O",  "duration": 5.0, "desc": "Block 50% damage for 5s"},
    POWERUP_SWORD:     {"name": "Flame Sword",    "color": (255, 140, 40),  "icon": "/",  "duration": 7.0, "desc": "+10 attack dmg for 7s"},
    POWERUP_FIRE_FIST: {"name": "Fire Fists",     "color": (255, 60, 20),   "icon": "F",  "duration": 6.0, "desc": "Burn damage on punch for 6s"},
}


class PowerUp:
    """A collectible power-up that spawns in the arena."""

    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.size = 20
        self.age = 0.0
        self.lifetime = 10.0  # disappears after 10s
        self.collected = False
        self.info = POWERUP_DEFS[kind]

    def update(self, dt):
        self.age += dt

    @property
    def alive(self):
        return not self.collected and self.age < self.lifetime

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def draw(self, surface, font):
        if not self.alive:
            return
        info = self.info
        # Pulsing glow
        pulse = 0.7 + 0.3 * math.sin(self.age * 4)
        r, g, b = info["color"]
        color = (int(r * pulse), int(g * pulse), int(b * pulse))

        # Outer glow
        glow = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*info["color"], 60), (self.size, self.size), self.size)
        surface.blit(glow, (self.x - self.size, self.y - self.size))

        # Main circle
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size // 2 + 2)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.size // 2 + 2, 2)

        # Icon letter
        icon_txt = font.render(info["icon"], True, (255, 255, 255))
        surface.blit(icon_txt, (self.x - icon_txt.get_width() // 2, self.y - icon_txt.get_height() // 2))

        # Remaining time indicator (fading border when about to expire)
        if self.lifetime - self.age < 3.0:
            blink = int(128 + 127 * math.sin(self.age * 8))
            pygame.draw.circle(surface, (255, 255, 255, blink), (int(self.x), int(self.y)), self.size // 2 + 5, 1)

    def apply(self, fighter):
        """Apply this power-up to a fighter."""
        self.collected = True
        kind = self.kind
        info = self.info

        if kind == POWERUP_HEALTH:
            fighter.hp = min(100, fighter.hp + 25)
        elif kind == POWERUP_STAMINA:
            fighter.stamina = min(100, fighter.stamina + 40)
        elif kind in (POWERUP_DAMAGE, POWERUP_SPEED, POWERUP_SHIELD, POWERUP_SWORD, POWERUP_FIRE_FIST):
            # Timed buffs
            fighter.active_buffs[kind] = info["duration"]

        # Always count toward quest progress
        fighter.powerups_collected += 1


class PowerUpSpawner:
    """Manages spawning power-ups at random intervals."""

    def __init__(self, arena_left, arena_right, ground_y):
        self.arena_left = arena_left + 60
        self.arena_right = arena_right - 60
        self.ground_y = ground_y
        self.timer = 0.0
        self.spawn_interval = 5.0  # spawn one every 5 seconds
        self.active_powerups = []
        self.max_active = 3

    def update(self, dt, fighters):
        self.timer += dt

        # Spawn new power-up
        if self.timer >= self.spawn_interval and len(self.active_powerups) < self.max_active:
            self.timer = 0.0
            self.spawn_interval = random.uniform(4.0, 8.0)
            kind = random.choice(list(POWERUP_DEFS.keys()))
            x = random.randint(self.arena_left, self.arena_right)
            y = self.ground_y - 15
            self.active_powerups.append(PowerUp(x, y, kind))

        # Update and check collisions
        for pu in self.active_powerups:
            pu.update(dt)
            if pu.collected:
                continue
            for fighter in fighters:
                fighter_rect = pygame.Rect(fighter.x, fighter.y, fighter.width, fighter.height)
                if fighter_rect.colliderect(pu.get_rect()):
                    pu.apply(fighter)

        # Clean up expired
        self.active_powerups = [pu for pu in self.active_powerups if pu.alive]

    def draw(self, surface, font):
        for pu in self.active_powerups:
            pu.draw(surface, font)

    def reset(self):
        self.active_powerups.clear()
        self.timer = 0.0


# ─── Quest System ────────────────────────────────────────────────────────────
QUEST_LAND_COMBOS    = "land_combos"
QUEST_BLOCK_ATTACKS  = "block_attacks"
QUEST_DODGE_ATTACKS  = "dodge_attacks"
QUEST_DEAL_DAMAGE    = "deal_damage"
QUEST_COLLECT_POWERUPS = "collect_powerups"
QUEST_WIN_FULL_HP    = "win_full_hp"

QUEST_DEFS = {
    QUEST_LAND_COMBOS:      {"desc": "Land {target} combos",       "target": 3, "reward_hp": 15, "reward_coord": 20},
    QUEST_BLOCK_ATTACKS:    {"desc": "Block {target} attacks",     "target": 5, "reward_hp": 10, "reward_coord": 15},
    QUEST_DODGE_ATTACKS:    {"desc": "Dodge {target} attacks",     "target": 3, "reward_hp": 10, "reward_coord": 25},
    QUEST_DEAL_DAMAGE:      {"desc": "Deal {target} total damage", "target": 40, "reward_hp": 20, "reward_coord": 10},
    QUEST_COLLECT_POWERUPS: {"desc": "Collect {target} power-ups", "target": 2, "reward_hp": 10, "reward_coord": 15},
    QUEST_WIN_FULL_HP:      {"desc": "Win round above 80 HP",      "target": 1, "reward_hp": 0,  "reward_coord": 30},
}


class Quest:
    """A mini-objective for a team during the match."""

    def __init__(self, quest_type):
        self.quest_type = quest_type
        info = QUEST_DEFS[quest_type]
        self.target = info["target"]
        self.progress = 0
        self.completed = False
        self.reward_hp = info["reward_hp"]
        self.reward_coord = info["reward_coord"]
        self.desc = info["desc"].format(target=self.target)
        self.just_completed = False  # for notification flash

    def increment(self, amount=1):
        if self.completed:
            return
        self.progress += amount
        if self.progress >= self.target:
            self.progress = self.target
            self.completed = True
            self.just_completed = True

    @property
    def ratio(self):
        return min(1.0, self.progress / self.target) if self.target > 0 else 1.0


class QuestManager:
    """Assigns and tracks quests for both teams."""

    def __init__(self):
        self.team_a_quests = []
        self.team_b_quests = []
        self.assign_quests()

    def assign_quests(self):
        """Give each team 2 random quests per round."""
        all_types = list(QUEST_DEFS.keys())
        random.shuffle(all_types)
        self.team_a_quests = [Quest(all_types[0]), Quest(all_types[1])]
        random.shuffle(all_types)
        self.team_b_quests = [Quest(all_types[0]), Quest(all_types[1])]

    def apply_rewards(self, fighter, quests):
        """Apply completed quest rewards to a fighter."""
        for q in quests:
            if q.just_completed:
                q.just_completed = False
                fighter.hp = min(100, fighter.hp + q.reward_hp)
                fighter.coordination = min(100, fighter.coordination + q.reward_coord)

    def reset(self):
        self.assign_quests()
