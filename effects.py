import pygame
import math
import random


class Particle:
    """A single particle with position, velocity, color, and lifetime."""

    def __init__(self, x, y, vx, vy, color, size=3, lifetime=0.6, gravity=0, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_size = size
        self.lifetime = lifetime
        self.age = 0.0
        self.gravity = gravity
        self.shrink = shrink

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        if self.shrink:
            ratio = 1.0 - (self.age / self.lifetime)
            self.size = max(0.5, self.max_size * ratio)

    @property
    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface, cam_offset_x=0, cam_offset_y=0):
        if not self.alive:
            return
        alpha = max(0, 1.0 - (self.age / self.lifetime))
        r, g, b = self.color[:3]
        px = int(self.x + cam_offset_x)
        py = int(self.y + cam_offset_y)
        s = max(1, int(self.size))
        # Draw with glow
        if s > 2:
            glow = pygame.Surface((s * 4, s * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (r, g, b, int(40 * alpha)), (s * 2, s * 2), s * 2)
            surface.blit(glow, (px - s * 2, py - s * 2))
        pygame.draw.circle(surface, (r, g, b), (px, py), s)


class ParticleSystem:
    """Manages all active particles."""

    def __init__(self):
        self.particles = []

    def emit_burst(self, x, y, color, count=12, speed=150, size=3, lifetime=0.5, gravity=200):
        """Emit a burst of particles in random directions."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.4, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd - 50  # bias upward
            sz = random.uniform(size * 0.5, size * 1.5)
            lt = random.uniform(lifetime * 0.5, lifetime)
            self.particles.append(Particle(x, y, vx, vy, color, sz, lt, gravity))

    def emit_sparks(self, x, y, color, count=8, speed=200):
        """Emit sharp sparks (small, fast, no gravity)."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            self.particles.append(Particle(x, y, vx, vy, color, 2, 0.3, 0, shrink=True))

    def emit_ring(self, x, y, color, count=16, radius_speed=200, lifetime=0.4):
        """Emit particles in an expanding ring (for power-up collect)."""
        for i in range(count):
            angle = (math.pi * 2 / count) * i
            vx = math.cos(angle) * radius_speed
            vy = math.sin(angle) * radius_speed
            self.particles.append(Particle(x, y, vx, vy, color, 2.5, lifetime, 0, shrink=True))

    def emit_trail(self, x, y, color, direction=-1):
        """Emit a small afterimage/trail particle."""
        self.particles.append(Particle(
            x + random.randint(-5, 5), y + random.randint(-10, 10),
            direction * random.uniform(10, 40), random.uniform(-20, 20),
            color, random.uniform(2, 5), 0.3, 0, shrink=True
        ))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface, cam_x=0, cam_y=0):
        for p in self.particles:
            p.draw(surface, cam_x, cam_y)

    def clear(self):
        self.particles.clear()


class ScreenShake:
    """Controls camera shake effect."""

    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.timer = 0
        self.offset_x = 0
        self.offset_y = 0

    def trigger(self, intensity=8, duration=0.15):
        self.intensity = intensity
        self.duration = duration
        self.timer = duration

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            ratio = self.timer / self.duration
            mag = self.intensity * ratio
            self.offset_x = random.uniform(-mag, mag)
            self.offset_y = random.uniform(-mag, mag)
        else:
            self.offset_x = 0
            self.offset_y = 0


class HitStop:
    """Pauses game logic for a few frames to sell impact."""

    def __init__(self):
        self.frames_remaining = 0

    def trigger(self, frames=3):
        self.frames_remaining = max(self.frames_remaining, frames)

    def should_pause(self):
        if self.frames_remaining > 0:
            self.frames_remaining -= 1
            return True
        return False


class DamageNumber:
    """A floating damage number with style."""

    def __init__(self, value, x, y, color, is_combo=False, text_override=None):
        self.text = text_override if text_override else f"-{value}"
        self.x = x + random.randint(-10, 10)
        self.y = y
        self.color = color
        self.size = 32 if is_combo else 24
        self.is_combo = is_combo
        self.lifetime = 1.2 if is_combo else 0.8
        self.age = 0.0
        self.vy = -60 if is_combo else -45
        self.scale = 1.5 if is_combo else 1.0

    def update(self, dt):
        self.age += dt
        self.y += self.vy * dt
        self.vy *= 0.97  # slow down
        if self.is_combo and self.age < 0.15:
            self.scale = 1.5 - (self.age / 0.15) * 0.5  # pop-in effect

    @property
    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface, fonts, cam_x=0, cam_y=0):
        if not self.alive:
            return
        alpha = max(0, 1.0 - (self.age / self.lifetime))
        sz = int(self.size * self.scale)
        font = fonts.get(sz)
        if not font:
            font = pygame.font.SysFont("Segoe UI", sz, bold=True)
            fonts[sz] = font

        # Shadow
        shadow = font.render(self.text, True, (0, 0, 0))
        shadow.set_alpha(int(alpha * 180))
        surface.blit(shadow, (int(self.x + cam_x) - shadow.get_width() // 2 + 2,
                              int(self.y + cam_y) + 2))
        # Main text
        txt = font.render(self.text, True, self.color)
        txt.set_alpha(int(alpha * 255))
        surface.blit(txt, (int(self.x + cam_x) - txt.get_width() // 2,
                           int(self.y + cam_y)))
