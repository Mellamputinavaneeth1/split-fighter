"""
lobby.py — Firebase-backed multiplayer lobby for Split Fighter.

Flow:
  HOME → Create Room → (Firebase room created) → Waiting Room (host + joiners pick slots)
  HOME → Join Room  → Enter code              → Pick slot → Waiting Room
"""

import pygame
import random
import math
import threading
import time as _time

try:
    from firebase_db import FirebaseDB, load_firebase_url
    _FIREBASE_AVAILABLE = True
except Exception:
    _FIREBASE_AVAILABLE = False

# ─── Screen IDs ──────────────────────────────────────────────────────────────
S_HOME     = "home"
S_CREATE   = "create"       # waiting room (host sees this after picking slot)
S_JOIN     = "join"         # code entry
S_SLOTS    = "slots"        # slot selection
S_WAITING  = "waiting"      # non-host waiting for game to start
S_ERROR    = "error"        # Firebase error / wrong code

SLOT_KEYS  = ["a_left", "b_left"]
SLOT_INFO  = {
    "a_left":  ("PLAYER 1", "Left side (Red)",   "P1"),
    "b_left":  ("PLAYER 2", "Right side (Blue)",  "P2"),
}

# ─── Colors ──────────────────────────────────────────────────────────────────
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
GRAY   = (130, 130, 140)
DARK   = (14, 14, 28)
DIM    = (55, 55, 75)
GOLD   = (255, 215, 0)
RED    = (220, 60, 60)
GREEN  = (60, 220, 100)
TA_C   = (230, 65, 65)
TB_C   = (65, 130, 230)
TA_L   = (255, 130, 90)
TB_L   = (90, 200, 255)

_FCACHE = {}
def fnt(name, size, bold=False):
    k = (name, size, bold)
    if k not in _FCACHE:
        _FCACHE[k] = pygame.font.SysFont(name, size, bold=bold)
    return _FCACHE[k]


class LobbyScreen:
    def __init__(self, width: int, height: int):
        self.W, self.H = width, height
        self.screen      = S_HOME
        self.sel         = 0           # home menu selection (0=create, 1=join)
        self.typing      = ""          # code entry input
        self.wrong_code  = False
        self.slot_cursor = 0
        self.time        = 0.0
        self.cursor_blink = 0.0
        self.spin_angle  = 0.0        # loading spinner

        # Firebase state
        self.db: FirebaseDB | None = None
        self.fb_ok       = False
        self.fb_error    = ""
        self.loading     = False       # True while a Firebase call is in flight
        self.loading_msg = ""

        # Room state (synced from Firebase)
        self.room_code   = ""
        self.my_slot     = ""         # the slot this device claimed
        self.is_host     = False
        self.live_slots  = {k: "" for k in SLOT_KEYS}  # polled from Firebase
        self._poll_thread: threading.Thread | None = None
        self._polling    = False

        # Result
        self.ready_to_start = False

        # Background particles
        self.particles = [
            {"x": random.randint(0, width), "y": random.randint(0, height),
             "vy": random.uniform(-18, -35), "r": random.uniform(1.0, 2.5),
             "a": random.randint(30, 90)}
            for _ in range(55)
        ]

        # Init Firebase in background
        self._init_firebase_async()

    # ── Firebase init ─────────────────────────────────────────────────────────
    def _init_firebase_async(self):
        self.loading = True
        self.loading_msg = "Connecting to database..."
        threading.Thread(target=self._do_init_firebase, daemon=True).start()

    def _do_init_firebase(self):
        try:
            self.db    = FirebaseDB()
            self.fb_ok = True
            self.fb_error = ""
        except Exception as e:
            self.fb_ok    = False
            self.fb_error = str(e)
        self.loading = False

    # ── Slot polling ──────────────────────────────────────────────────────────
    def _start_polling(self):
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._polling = False

    def _poll_loop(self):
        while self._polling and self.room_code:
            try:
                slots = self.db.get_slots(self.room_code)
                if isinstance(slots, dict):
                    self.live_slots = {k: slots.get(k, "") for k in SLOT_KEYS}
                # Check if host has set status to "starting"
                room = self.db.get_room(self.room_code)
                if room and room.get("status") == "starting" and not self.is_host:
                    self.ready_to_start = True
            except Exception:
                pass
            _time.sleep(0.6)

    # ── Firebase actions (run in threads to avoid blocking) ───────────────────
    def _do_create_room(self):
        self.loading = True
        self.loading_msg = "Creating room..."
        for attempt in range(5):
            code = str(random.randint(1000, 9999))
            try:
                if self.db.create_room(code, host_slot=self.my_slot):
                    self.room_code = code
                    self.loading   = False
                    self.loading_msg = ""
                    # Claim the host's slot
                    self.db.claim_slot(code, self.my_slot,
                                       SLOT_INFO[self.my_slot][2])
                    self.live_slots[self.my_slot] = SLOT_INFO[self.my_slot][2]
                    self._start_polling()
                    self.screen = S_CREATE
                    return
            except Exception as e:
                pass
        self.loading  = False
        self.fb_error = "Could not create room — check your internet."
        self.screen   = S_ERROR

    def _do_join_room(self, code: str):
        self.loading     = True
        self.loading_msg = f"Looking up room {code}..."
        try:
            room = self.db.get_room(code)
            if not room:
                self.loading    = False
                self.wrong_code = True
                self.typing     = ""
                return
            if room.get("status") not in ("lobby",):
                self.loading    = False
                self.fb_error   = f"Room {code} already in progress."
                self.wrong_code = True
                self.typing     = ""
                return
            # Room found — go to slot selection
            self.room_code      = code
            self.live_slots     = {k: room.get("slots", {}).get(k, "") for k in SLOT_KEYS}
            self._start_polling()
            self.loading        = False
            self.wrong_code     = False
            # Move cursor to first empty slot
            first = next((i for i, k in enumerate(SLOT_KEYS) if not self.live_slots[k]), 0)
            self.slot_cursor = first
            self.screen = S_SLOTS
        except Exception as e:
            self.loading    = False
            self.fb_error   = f"Error: {e}"
            self.screen     = S_ERROR

    def _do_claim_slot(self, slot: str):
        self.loading     = True
        self.loading_msg = "Claiming slot..."
        label = SLOT_INFO[slot][2]
        try:
            ok = self.db.claim_slot(self.room_code, slot, label)
            if ok:
                self.my_slot               = slot
                self.live_slots[slot]      = label
                self.loading               = False
                self.screen = S_CREATE if self.is_host else S_WAITING
            else:
                self.loading    = False
                self.fb_error   = "Slot was taken — pick another."
                self.screen     = S_SLOTS
        except Exception as e:
            self.loading    = False
            self.fb_error   = str(e)

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, dt: float):
        self.time         += dt
        self.cursor_blink += dt
        self.spin_angle   += dt * 200   # degrees/s
        for p in self.particles:
            p["y"] += p["vy"] * dt
            if p["y"] < -5:
                p["y"] = self.H + 5
                p["x"] = random.randint(0, self.W)

    # ── Events ────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN or self.loading:
            return
        key = event.key
        if   self.screen == S_HOME:    self._ev_home(key)
        elif self.screen == S_JOIN:    self._ev_join(key, event.unicode)
        elif self.screen == S_SLOTS:   self._ev_slots(key)
        elif self.screen == S_CREATE:  self._ev_create(key)
        elif self.screen == S_WAITING: self._ev_waiting(key)
        elif self.screen == S_ERROR:   self._ev_error(key)

    def _ev_home(self, key):
        if key == pygame.K_UP:   self.sel = (self.sel - 1) % 2
        elif key == pygame.K_DOWN: self.sel = (self.sel + 1) % 2
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if not self.fb_ok:
                self.screen = S_ERROR
                self.fb_error = ("Firebase not connected.\n"
                                 "Edit config.json with your Firebase URL.")
                return
            if self.sel == 0:
                # Host: pick slot first, then create room
                self.is_host     = True
                self.slot_cursor = 0
                self.screen      = S_SLOTS
            else:
                self.screen  = S_JOIN
                self.typing  = ""
                self.wrong_code = False

    def _ev_join(self, key, ch):
        if key == pygame.K_ESCAPE:
            self.screen = S_HOME; self.typing = ""; self.wrong_code = False
        elif key == pygame.K_BACKSPACE:
            self.typing = self.typing[:-1]; self.wrong_code = False
        elif ch.isdigit() and len(self.typing) < 4:
            self.typing += ch; self.wrong_code = False
            if len(self.typing) == 4:
                self._launch(self._do_join_room, self.typing)

    def _ev_slots(self, key):
        if key == pygame.K_ESCAPE:
            self.screen = S_HOME if not self.room_code else (S_CREATE if self.is_host else S_WAITING)
        elif key == pygame.K_UP:
            self.slot_cursor = (self.slot_cursor - 1) % len(SLOT_KEYS)
        elif key == pygame.K_DOWN:
            self.slot_cursor = (self.slot_cursor + 1) % len(SLOT_KEYS)
        elif key == pygame.K_RETURN:
            sk = SLOT_KEYS[self.slot_cursor]
            if self.live_slots.get(sk):
                return   # already taken
            if self.is_host and not self.room_code:
                # Host hasn't created room yet — create after claiming slot
                self.my_slot = sk
                self._launch(self._do_create_room)
            else:
                self._launch(self._do_claim_slot, sk)

    def _ev_create(self, key):
        if key == pygame.K_ESCAPE:
            self._stop_polling(); self.screen = S_HOME
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if any(self.live_slots.values()):
                self._launch(self._set_starting)

    def _ev_waiting(self, key):
        if key == pygame.K_ESCAPE:
            self._stop_polling(); self.screen = S_HOME

    def _ev_error(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.screen = S_HOME; self.fb_error = ""

    def _set_starting(self):
        try:
            self.db.set_status(self.room_code, "starting")
            self.ready_to_start = True
        except Exception as e:
            self.fb_error = str(e)

    def _launch(self, fn, *args):
        """Run a Firebase function in a background thread."""
        threading.Thread(target=fn, args=args, daemon=True).start()

    # ── Config export ─────────────────────────────────────────────────────────
    def get_config(self) -> dict:
        team = "A" if self.my_slot.startswith("a") else "B"
        role = "left" if self.my_slot.endswith("left") else "right"
        return {
            "db":          self.db,
            "room_code":   self.room_code,
            "my_slot":     self.my_slot,
            "is_host":     self.is_host,
            "perspective": team,
            "player_role": role,
            "slots":       dict(self.live_slots),
        }

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        surface.fill(DARK)
        self._draw_bg(surface)
        if   self.screen == S_HOME:    self._draw_home(surface)
        elif self.screen == S_CREATE:  self._draw_create(surface)
        elif self.screen == S_JOIN:    self._draw_join(surface)
        elif self.screen == S_SLOTS:   self._draw_slots(surface)
        elif self.screen == S_WAITING: self._draw_waiting(surface)
        elif self.screen == S_ERROR:   self._draw_error(surface)
        if self.loading:
            self._draw_loading(surface)
        # DB status dot
        dot_col = GREEN if self.fb_ok else (RED if not self.loading else (200, 160, 40))
        pygame.draw.circle(surface, dot_col, (self.W - 14, 14), 5)

    def _draw_bg(self, s):
        for p in self.particles:
            pulse = 0.5 + 0.5 * math.sin(self.time * 2 + p["x"] * 0.02)
            a = int(p["a"] * pulse)
            pygame.draw.circle(s, (a, a, min(255, int(a * 1.3))),
                               (int(p["x"]), int(p["y"])), max(1, int(p["r"])))

    def _draw_title(self, s, subtitle=""):
        cx = self.W // 2
        t = fnt("Segoe UI", 52, True).render("SPLIT FIGHTER", True, WHITE)
        s.blit(t, (cx - t.get_width() // 2, 28))
        if subtitle:
            sub = fnt("Segoe UI", 19, True).render(subtitle, True, GRAY)
            s.blit(sub, (cx - sub.get_width() // 2, 88))

    def _draw_loading(self, s):
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        s.blit(ov, (0, 0))
        cx, cy = self.W // 2, self.H // 2
        r, t = 24, self.spin_angle
        for i in range(8):
            a = math.radians(t + i * 45)
            alpha = int(255 * (i + 1) / 8)
            pygame.draw.circle(s, (alpha, alpha, alpha),
                               (int(cx + r * math.cos(a)), int(cy + r * math.sin(a))), 4)
        msg = fnt("Segoe UI", 16, True).render(self.loading_msg, True, GRAY)
        s.blit(msg, (cx - msg.get_width() // 2, cy + 40))

    def _draw_home(self, s):
        self._draw_title(s, "2v2 TEAM FIGHTING GAME")
        cx, cy = self.W // 2, self.H // 2
        if not self.fb_ok and not self.loading:
            warn = fnt("Segoe UI", 13).render(
                "⚠  Firebase not connected — edit config.json first", True, (255, 120, 50))
            s.blit(warn, (cx - warn.get_width() // 2, 115))
        options = [("CREATE ROOM", "Host a game — others join with your code"),
                   ("JOIN ROOM",   "Enter a 4-digit code to join")]
        bw, bh = 380, 80
        for i, (lbl, desc) in enumerate(options):
            bx = cx - bw // 2
            by = cy - 60 + i * (bh + 22)
            sel = i == self.sel
            bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg.fill(((55, 55, 90, 220) if sel else (35, 35, 60, 200)))
            s.blit(bg, (bx, by))
            border = GOLD if sel else DIM
            pygame.draw.rect(s, border, (bx, by, bw, bh), 2 if sel else 1, border_radius=6)
            if sel:
                glow = pygame.Surface((bw + 20, bh + 20), pygame.SRCALPHA)
                p = int(18 + 14 * math.sin(self.time * 4))
                pygame.draw.rect(glow, (255, 215, 0, p), (0, 0, bw + 20, bh + 20), border_radius=8)
                s.blit(glow, (bx - 10, by - 10))
            lt = fnt("Segoe UI", 22, True).render(lbl, True, GOLD if sel else WHITE)
            s.blit(lt, (cx - lt.get_width() // 2, by + 12))
            dt = fnt("Segoe UI", 13).render(desc, True, GRAY)
            s.blit(dt, (cx - dt.get_width() // 2, by + 46))
        hint = fnt("Segoe UI", 12).render("UP / DOWN = Navigate    ENTER = Select", True, DIM)
        s.blit(hint, (cx - hint.get_width() // 2, self.H - 30))

    def _draw_create(self, s):
        self._draw_title(s, "WAITING ROOM")
        cx = self.W // 2
        # Code display
        cb = pygame.Surface((300, 78), pygame.SRCALPHA); cb.fill((0, 0, 0, 160))
        s.blit(cb, (cx - 150, 108))
        pygame.draw.rect(s, GOLD, (cx - 150, 108, 300, 78), 2, border_radius=6)
        cl = fnt("Segoe UI", 13).render("ROOM CODE — Share with players:", True, GRAY)
        s.blit(cl, (cx - cl.get_width() // 2, 114))
        pulse = 0.85 + 0.15 * math.sin(self.time * 3)
        cc = (int(255 * pulse), int(215 * pulse), 0)
        ct = fnt("Consolas", 38, True).render(self.room_code, True, cc)
        s.blit(ct, (cx - ct.get_width() // 2, 138))
        # Slots
        self._draw_slot_grid(s, cx, 205, False)
        # Hints
        for i, h in enumerate(["[SPACE / ENTER] = Start game when everyone is ready",
                                "[ESC] = Back to home"]):
            ht = fnt("Segoe UI", 12).render(h, True, DIM)
            s.blit(ht, (cx - ht.get_width() // 2, self.H - 62 + i * 18))
        # Start btn
        can = any(self.live_slots.values())
        bc  = GOLD if can else DIM
        bt  = fnt("Segoe UI", 18, True).render(
            "PRESS SPACE TO START" if can else "Waiting for players...", True, bc)
        if not can or int(self.time * 2) % 2 == 0:
            s.blit(bt, (cx - bt.get_width() // 2, self.H - 36))

    def _draw_join(self, s):
        self._draw_title(s, "JOIN A ROOM")
        cx, cy = self.W // 2, self.H // 2
        bw, bh = 360, 100
        bx, by = cx - bw // 2, cy - bh // 2 - 20
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA); bg.fill((0, 0, 0, 160))
        s.blit(bg, (bx, by))
        bc = RED if self.wrong_code else GOLD
        pygame.draw.rect(s, bc, (bx, by, bw, bh), 2, border_radius=6)
        pl = fnt("Segoe UI", 15, True).render("Enter Room Code:", True, GRAY)
        s.blit(pl, (cx - pl.get_width() // 2, by + 10))
        padded = ""
        for i in range(4):
            if i < len(self.typing): padded += self.typing[i] + "  "
            elif i == len(self.typing): padded += ("|" if int(self.cursor_blink * 2) % 2 == 0 else "_") + "  "
            else: padded += "_  "
        dc = RED if self.wrong_code else WHITE
        dt = fnt("Consolas", 38, True).render(padded.strip(), True, dc)
        s.blit(dt, (cx - dt.get_width() // 2, by + 44))
        if self.wrong_code:
            et = fnt("Segoe UI", 14, True).render("Room not found — try again", True, RED)
            s.blit(et, (cx - et.get_width() // 2, by + bh + 8))
        for i, h in enumerate(["Type the 4-digit code from the host's screen",
                                "Auto-confirms on 4th digit    ESC = Back"]):
            ht = fnt("Segoe UI", 13).render(h, True, GRAY)
            s.blit(ht, (cx - ht.get_width() // 2, by + bh + (34 if self.wrong_code else 16) + i * 20))

    def _draw_slots(self, s):
        self._draw_title(s, "CHOOSE YOUR SLOT")
        cx = self.W // 2
        self._draw_slot_grid(s, cx, 135, True)
        sk = SLOT_KEYS[self.slot_cursor]
        taken = bool(self.live_slots.get(sk))
        info = SLOT_INFO[sk]
        status = "(taken)" if taken else "(press ENTER to claim)"
        st = fnt("Segoe UI", 13).render(
            f"Selected: {info[0]}  {info[1].strip()}  {status}", True, GOLD)
        s.blit(st, (cx - st.get_width() // 2, self.H - 95))
        for i, h in enumerate(["UP / DOWN = Move    ENTER = Claim slot",
                                "ESC = Back"]):
            ht = fnt("Segoe UI", 12).render(h, True, DIM)
            s.blit(ht, (cx - ht.get_width() // 2, self.H - 68 + i * 18))

    def _draw_waiting(self, s):
        self._draw_title(s, "WAITING FOR HOST TO START")
        cx = self.W // 2
        cb = pygame.Surface((300, 54), pygame.SRCALPHA); cb.fill((0, 0, 0, 150))
        s.blit(cb, (cx - 150, 108))
        pygame.draw.rect(s, GOLD, (cx - 150, 108, 300, 54), 2, border_radius=6)
        cl = fnt("Segoe UI", 13).render("Room Code:", True, GRAY)
        s.blit(cl, (cx - cl.get_width() // 2, 114))
        ct = fnt("Consolas", 28, True).render(self.room_code, True, GOLD)
        s.blit(ct, (cx - ct.get_width() // 2, 134))
        # Live slots
        self._draw_slot_grid(s, cx, 185, False)
        # Spinner hint
        dots = "." * (int(self.time * 2) % 4)
        wt = fnt("Segoe UI", 16, True).render(
            f"Your slot: {SLOT_INFO[self.my_slot][0]} {SLOT_INFO[self.my_slot][1].strip()}", True, GOLD)
        s.blit(wt, (cx - wt.get_width() // 2, self.H - 55))
        hint = fnt("Segoe UI", 14).render(
            f"Waiting for host to press SPACE{dots}", True, GRAY)
        s.blit(hint, (cx - hint.get_width() // 2, self.H - 30))

    def _draw_error(self, s):
        self._draw_title(s, "ERROR")
        cx, cy = self.W // 2, self.H // 2
        lines = self.fb_error.split("\n")
        for i, line in enumerate(lines):
            lt = fnt("Segoe UI", 15).render(line, True, (255, 100, 100))
            s.blit(lt, (cx - lt.get_width() // 2, cy - 30 + i * 24))
        hint = fnt("Segoe UI", 14).render("Press ENTER or ESC to go back", True, GRAY)
        s.blit(hint, (cx - hint.get_width() // 2, cy + 80))

    def _draw_slot_grid(self, s, cx, start_y, show_cursor):
        sw, sh, gap = 500, 60, 10
        dy = start_y
        prev_team = None
        for i, sk in enumerate(SLOT_KEYS):
            team, side, _ = SLOT_INFO[sk]
            tc   = TA_C if team == "TEAM A" else TB_C
            sel  = show_cursor and i == self.slot_cursor
            taken = bool(self.live_slots.get(sk))
            if team != prev_team:
                ht = fnt("Segoe UI", 14, True).render(team, True, tc)
                s.blit(ht, (cx - sw // 2, dy))
                pygame.draw.line(s, tc, (cx - sw // 2, dy + 19), (cx + sw // 2, dy + 19), 1)
                dy += 26; prev_team = team
            bx = cx - sw // 2
            bg_c = ((int(tc[0]*.22), int(tc[1]*.22), int(tc[2]*.22)) if taken else (26, 26, 46))
            bg = pygame.Surface((sw, sh), pygame.SRCALPHA)
            bg.fill((*bg_c, 210)); s.blit(bg, (bx, dy))
            border = tc if (sel or taken) else DIM
            pygame.draw.rect(s, border, (bx, dy, sw, sh), 2 if (sel or taken) else 1, border_radius=5)
            if sel:
                g = pygame.Surface((sw + 14, sh + 14), pygame.SRCALPHA)
                p = int(22 + 18 * math.sin(self.time * 5))
                pygame.draw.rect(g, (*tc, p), (0, 0, sw + 14, sh + 14), border_radius=7)
                s.blit(g, (bx - 7, dy - 7))
            rt = fnt("Segoe UI", 14, True).render(side.strip(), True, tc if taken else GRAY)
            s.blit(rt, (bx + 14, dy + 10))
            dt = fnt("Segoe UI", 11).render("Left-side controls" if "LEFT" in side else "Right-side controls", True, DIM)
            s.blit(dt, (bx + 14, dy + 32))
            bw2, bh2 = 90, 26
            badgex = bx + sw - bw2 - 12; badgey = dy + (sh - bh2) // 2
            bdg = pygame.Surface((bw2, bh2), pygame.SRCALPHA)
            bdg.fill((*tc, 55) if taken else (40, 40, 60, 140)); s.blit(bdg, (badgex, badgey))
            pygame.draw.rect(s, tc if taken else DIM, (badgex, badgey, bw2, bh2), 1, border_radius=4)
            label = self.live_slots.get(sk) or "EMPTY"
            bt = fnt("Segoe UI", 13, True).render(label, True, tc if taken else GRAY)
            s.blit(bt, (badgex + bw2 // 2 - bt.get_width() // 2, badgey + bh2 // 2 - bt.get_height() // 2))
            if sel:
                pygame.draw.polygon(s, GOLD, [(bx + sw + 10, dy + sh // 2),
                                              (bx + sw, dy + sh // 2 - 7),
                                              (bx + sw, dy + sh // 2 + 7)])
            dy += sh + gap
