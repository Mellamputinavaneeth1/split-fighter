"""
main.py -- Split Fighter: 1v1 Arena Brawl (Firebase multiplayer)

HOST  -- runs game logic, pushes state to Firebase, reads remote inputs
CLIENT -- reads state from Firebase, pushes own inputs, renders
"""

import pygame
import sys
import math
import time as _time
import threading
import asyncio

from fighter import Fighter, WEAPON_DEFS
from arena import Arena, Arrow, GROUND_Y
from effects import ParticleSystem, ScreenShake, HitStop, DamageNumber
from lobby import LobbyScreen
from firebase_db import FirebaseDB

# --- Window -------------------------------------------------------------------
W_WIDTH   = 1100
W_HEIGHT  = 700
FPS       = 60
SYNC_RATE = 2     # push/pull Firebase every N frames (~30fps sync)

# --- Colors -------------------------------------------------------------------
WHITE    = (255, 255, 255)
BLACK    = (0, 0, 0)
GRAY     = (130, 130, 140)
DIM      = (55, 55, 75)
GOLD     = (255, 215, 0)
RED      = (220, 60, 60)
GREEN    = (60, 220, 100)
P1_COL   = (230, 80, 80)      # red-ish
P1_LIGHT = (255, 140, 100)
P2_COL   = (80, 140, 230)     # blue-ish
P2_LIGHT = (100, 180, 255)
HP_BG    = (50, 20, 20)
HP_G     = (50, 220, 80)
HP_Y     = (240, 200, 40)
HP_O     = (255, 140, 40)
HP_R     = (220, 50, 40)

_FONTS = {}
def gf(name, size, bold=False):
    k = (name, size, bold)
    if k not in _FONTS:
        _FONTS[k] = pygame.font.SysFont(name, size, bold=bold)
    return _FONTS[k]

def hp_color(hp):
    if hp > 65: return HP_G
    if hp > 40: return HP_Y
    if hp > 20: return HP_O
    return HP_R


# --- Stick figure drawing -----------------------------------------------------
def draw_fighter(surface, f: Fighter, cam_x=0, cam_y=0):
    cx = int(f.center_x + cam_x)
    by = int(f.y + cam_y)
    d  = f.facing
    flash = f.hit_flash > 0
    body = WHITE if flash else f.color

    head_r = 14
    head_y = by + 14
    neck_y = head_y + head_r
    hip_y  = neck_y + 35

    # Coordination boost aura (4P mode)
    if getattr(f, 'coord_glow', False):
        aura = pygame.Surface((80, 110), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (255, 215, 0, 50), (0, 0, 80, 110))
        pygame.draw.ellipse(aura, (255, 230, 120, 100), (4, 4, 72, 102), 2)
        surface.blit(aura, (cx - 40, int(head_y - 18)))

    # Head
    pygame.draw.circle(surface, body, (cx, int(head_y)), head_r)
    pygame.draw.circle(surface, WHITE, (cx, int(head_y)), head_r, 2)
    # Eyes
    for ox in (-4, 4):
        pygame.draw.circle(surface, WHITE, (cx + d * 4 + ox, int(head_y) - 2), 3)
        pygame.draw.circle(surface, BLACK, (cx + d * 4 + ox + d, int(head_y) - 2), 1)

    # Torso
    pygame.draw.line(surface, WHITE, (cx, int(neck_y)), (cx, int(hip_y)), 4)

    # Player label
    lbl = gf("Segoe UI", 11, True).render(f.player_id, True, f.color)
    surface.blit(lbl, (cx - lbl.get_width() // 2, int(head_y) - 28))

    # Weapon label
    wname = WEAPON_DEFS.get(f.weapon, {}).get("name", "")
    if wname and f.weapon != "fists":
        wt = gf("Segoe UI", 10).render(wname, True, GOLD)
        surface.blit(wt, (cx - wt.get_width() // 2, int(hip_y) + 42))

    # -- Arms --------------------------------------------------------------
    arm_start = (cx, int(neck_y + 6))
    arm_len1, arm_len2 = 18, 20

    def draw_arm(start, a1, l1, a2, l2, color, thick=3):
        mx = start[0] + int(math.cos(a1) * l1)
        my = start[1] + int(math.sin(a1) * l1)
        ex = mx + int(math.cos(a2) * l2)
        ey = my + int(math.sin(a2) * l2)
        pygame.draw.line(surface, color, start, (mx, my), thick)
        pygame.draw.line(surface, color, (mx, my), (ex, ey), thick)
        pygame.draw.circle(surface, color, (mx, my), thick)
        return (ex, ey)

    if f.is_attacking and f.attack_anim > 0:
        # Attack swing animation
        swing = 1.0 - (f.attack_anim / 0.2)  # 0RIGHT1
        swing_a = math.pi * 0.5 + d * swing * 1.2
        end = draw_arm(arm_start, swing_a - 0.3, arm_len1, swing_a + 0.2, arm_len2,
                       (255, 200, 80), 4)
        # Weapon tip
        if f.weapon == "sword":
            tip_x = end[0] + d * 20
            pygame.draw.line(surface, (200, 220, 255), end, (tip_x, end[1] - 8), 3)
            pygame.draw.circle(surface, (255, 255, 255), (tip_x, end[1] - 8), 3)
        elif f.weapon == "axe":
            tip_x = end[0] + d * 14
            pygame.draw.line(surface, (180, 140, 80), end, (tip_x, end[1] - 5), 4)
            pygame.draw.polygon(surface, (200, 160, 100),
                                [(tip_x, end[1] - 12), (tip_x + d * 8, end[1] - 5),
                                 (tip_x, end[1] + 2)])
        elif f.weapon == "bow":
            # Draw bow arc
            pygame.draw.arc(surface, (160, 200, 120),
                            (end[0] - 10, end[1] - 15, 20, 30),
                            math.pi * 0.3, math.pi * 1.7, 2)
        else:
            pygame.draw.circle(surface, (255, 120, 60), end, 6)
        # Other arm relaxed
        draw_arm((cx, int(neck_y + 6)), math.pi * 0.6 - d * 0.2, arm_len1,
                 math.pi * 0.5, arm_len2, body)
    elif f.blocking:
        # Both arms up in guard
        for side in (-1, 1):
            draw_arm((cx + side * 3, int(neck_y + 6)),
                     math.pi * 0.85 + side * 0.3, arm_len1,
                     math.pi * 1.3 + side * 0.2, arm_len2, (100, 160, 255), 4)
        if f.weapon == "shield":
            # Draw shield
            sx = cx + d * 22
            sy = int(neck_y + 15)
            pygame.draw.ellipse(surface, (80, 140, 220), (sx - 10, sy - 15, 20, 30))
            pygame.draw.ellipse(surface, (120, 180, 255), (sx - 10, sy - 15, 20, 30), 2)
    else:
        # Idle arms
        for side_off in (-3, 3):
            draw_arm((cx + side_off, int(neck_y + 6)),
                     math.pi * 0.6 + side_off * 0.03, arm_len1,
                     math.pi * 0.5, arm_len2, body)
        # Show held weapon
        if f.weapon == "sword":
            wx = cx + d * 25
            wy = int(neck_y + 28)
            pygame.draw.line(surface, (180, 200, 220), (cx + d * 18, int(neck_y + 22)),
                             (wx, wy - 12), 2)
        elif f.weapon == "axe":
            wx = cx + d * 22
            wy = int(neck_y + 26)
            pygame.draw.line(surface, (160, 120, 70), (cx + d * 16, int(neck_y + 20)),
                             (wx, wy), 2)
        elif f.weapon == "bow":
            wx = cx + d * 20
            wy = int(neck_y + 18)
            pygame.draw.arc(surface, (140, 180, 110),
                            (wx - 6, wy - 12, 12, 24), math.pi * 0.3, math.pi * 1.7, 2)

    # -- Legs --------------------------------------------------------------
    leg_len1, leg_len2 = 20, 22
    if not f.on_ground:
        # In-air legs
        for side in (-1, 1):
            draw_arm((cx + side * 4, int(hip_y)),
                     math.pi * 0.45 + side * 0.15, leg_len1,
                     math.pi * 0.55 + side * 0.1, leg_len2, body)
    elif abs(f.vx) > 10:
        # Running animation
        t = _time.time() * 8
        for side in (-1, 1):
            off = math.sin(t + side) * 0.3
            draw_arm((cx + side * 4, int(hip_y)),
                     math.pi * 0.5 + off, leg_len1,
                     math.pi * 0.45 + off * 0.5, leg_len2, body)
    else:
        # Standing
        for side in (-1, 1):
            draw_arm((cx + side * 4, int(hip_y)),
                     math.pi * 0.55 + side * 0.08, leg_len1,
                     math.pi * 0.48, leg_len2, body)

    # -- Block indicator ---------------------------------------------------
    if f.blocking:
        shield_s = pygame.Surface((50, 70), pygame.SRCALPHA)
        p = int(50 + 30 * math.sin(_time.time() * 5))
        pygame.draw.ellipse(shield_s, (100, 180, 255, p), (0, 0, 50, 70))
        surface.blit(shield_s, (cx - 25, int(head_y) - 10))


# --- HUD ---------------------------------------------------------------------
def draw_hp_bar(surface, x, y, w, h, hp, max_hp, color, right=False):
    ratio = max(0.0, min(1.0, hp / max_hp))
    pygame.draw.rect(surface, HP_BG, (x, y, w, h), border_radius=4)
    fw = int(w * ratio)
    if right:
        pygame.draw.rect(surface, color, (x + w - fw, y, fw, h), border_radius=4)
    else:
        pygame.draw.rect(surface, color, (x, y, fw, h), border_radius=4)
    pygame.draw.rect(surface, WHITE, (x, y, w, h), 1, border_radius=4)


# --- MAIN ---------------------------------------------------------------------
async def main():
    pygame.init()
    screen = pygame.display.set_mode((W_WIDTH, W_HEIGHT))
    pygame.display.set_caption("SPLIT FIGHTER -- Arena Brawl")
    clock = pygame.time.Clock()

    # -- Lobby -----------------------------------------------------------------
    lobby = LobbyScreen(W_WIDTH, W_HEIGHT)
    while not lobby.ready_to_start:
        dt = clock.tick(FPS) / 1000.0
        lobby.update(dt)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            lobby.handle_event(ev)
        lobby.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)

    # Flush event queue so stale ENTER/SPACE from lobby doesn't affect game
    pygame.event.clear()
    pygame.time.wait(100)    # brief pause to let key releases register
    pygame.event.clear()

    config    = lobby.get_config()
    db: FirebaseDB = config["db"]
    room_code = config["room_code"]
    my_slot   = config["my_slot"]
    is_host   = config["is_host"]
    game_mode = config.get("game_mode", "2p")
    my_role   = config.get("player_role", "mover")
    my_team   = config.get("perspective", "A")

    is_4p   = game_mode == "4p"
    i_am_p1 = my_slot.startswith("a")
    if is_4p:
        my_id = f"TEAM {my_team} ({my_role.upper()})"
    else:
        my_id = "P1" if i_am_p1 else "P2"

    # -- Create game objects ---------------------------------------------------
    arena = Arena(W_WIDTH, W_HEIGHT)
    p1_name = "TEAM A" if is_4p else "P1"
    p2_name = "TEAM B" if is_4p else "P2"
    p1 = Fighter(80,  GROUND_Y - 100, P1_COL, p1_name, team="A")
    p2 = Fighter(980, GROUND_Y - 100, P2_COL, p2_name, team="B")
    p1.facing = 1; p2.facing = -1

    my_fighter    = p1 if i_am_p1 else p2
    other_fighter = p2 if i_am_p1 else p1

    particles  = ParticleSystem()
    shake      = ScreenShake()
    hitstop    = HitStop()
    dmg_numbers = []

    game_over    = False
    winner       = ""
    game_time    = 0.0
    frame_count  = 0
    ctrl_fade    = 6.0    # seconds to show controls hint
    pickup_hint  = ""     # shows "Press E to pick up SWORD" etc
    pickup_timer = 0.0

    # -- Firebase sync state ---------------------------------------------------
    _remote_state  = {}
    _remote_input  = {}
    _sync_lock     = threading.Lock()
    _sync_running  = True

    def _host_sync_loop():
        while _sync_running:
            try:
                with _sync_lock:
                    snap = dict(_remote_state)
                if snap:
                    db.push_game_state(room_code, snap)
                inp = db.pull_inputs(room_code)
                if isinstance(inp, dict):
                    with _sync_lock:
                        _remote_input.clear()
                        _remote_input.update(inp)
            except Exception:
                pass
            _time.sleep(0.05)

    def _client_sync_loop():
        while _sync_running:
            try:
                gs = db.pull_game_state(room_code)
                if isinstance(gs, dict) and gs:
                    with _sync_lock:
                        _remote_state.clear()
                        _remote_state.update(gs)
            except Exception:
                pass
            _time.sleep(0.033)  # ~30fps polling for smoother interpolation

    sync_thread = threading.Thread(
        target=_host_sync_loop if is_host else _client_sync_loop, daemon=True)
    sync_thread.start()

    # -- Client interpolation state --------------------------------------------
    # Instead of snapping fighter positions from Firebase snapshots (which causes
    # the opponent to appear laggy/stuttery), we store the target positions and
    # smoothly interpolate towards them every frame at 60fps.
    _interp_speed = 18.0  # lerp factor per second (higher = faster catch-up)
    _p1_target = {"x": p1.x, "y": p1.y, "vx": p1.vx, "vy": p1.vy}
    _p2_target = {"x": p2.x, "y": p2.y, "vx": p2.vx, "vy": p2.vy}
    _last_gs_ts = 0.0  # timestamp of last received game state

    # -- Input state for my fighter --------------------------------------------
    move_dir   = 0    # -1, 0, 1 (mover or 2P)
    face_dir   = 0    # -1, 0, 1 (attacker in 4P)
    want_jump  = False
    want_atk   = False
    want_block = False
    want_pickup = False

    # -- Game loop -------------------------------------------------------------
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        game_time += dt
        frame_count += 1

        if hitstop.should_pause():
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: running = False
            pygame.display.flip()
            continue

        # -- Events ------------------------------------------------------------
        want_jump   = False
        want_atk    = False
        want_pickup = False

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False

                # Restart on game over
                if game_over and ev.key == pygame.K_RETURN and is_host:
                    p1.reset(80, GROUND_Y - 100); p2.reset(980, GROUND_Y - 100)
                    p1.facing = 1; p2.facing = -1
                    arena.reset(); particles.clear(); dmg_numbers.clear()
                    game_over = False; winner = ""
                    continue

                if game_over:
                    continue

                if is_4p:
                    if my_role == "mover":
                        if ev.key in (pygame.K_w, pygame.K_SPACE):
                            want_jump = True
                        if ev.key == pygame.K_e:
                            want_pickup = True
                    elif my_role == "attacker":
                        if ev.key == pygame.K_j:
                            want_atk = True
                        if ev.key == pygame.K_k:
                            want_block = True
                else:
                    if ev.key in (pygame.K_w, pygame.K_SPACE):
                        want_jump = True
                    if ev.key == pygame.K_j:
                        want_atk = True
                    if ev.key == pygame.K_e:
                        want_pickup = True
                    if ev.key == pygame.K_k:
                        want_block = True

            elif ev.type == pygame.KEYUP:
                if ev.key == pygame.K_k:
                    want_block = False

        # Continuous movement keys
        keys = pygame.key.get_pressed()
        move_dir = 0
        face_dir = 0
        if not game_over:
            if is_4p:
                if my_role == "mover":
                    if keys[pygame.K_a]: move_dir -= 1
                    if keys[pygame.K_d]: move_dir += 1
                elif my_role == "attacker":
                    if keys[pygame.K_a]: face_dir -= 1
                    if keys[pygame.K_d]: face_dir += 1
                    want_block = keys[pygame.K_k]
            else:
                if keys[pygame.K_a]: move_dir -= 1
                if keys[pygame.K_d]: move_dir += 1
                want_block = keys[pygame.K_k]

        # -- Apply local input to my fighter -----------------------------------
        if not game_over:
            if is_4p:
                if my_role == "mover":
                    my_fighter.move_input(move_dir)
                    if want_jump:
                        my_fighter.jump()
                    if want_pickup:
                        _handle_pickup(my_fighter, arena)
                elif my_role == "attacker":
                    my_fighter.face_input(face_dir)
                    if want_atk:
                        my_fighter.attack()
                    if want_block:
                        my_fighter.start_block()
                    else:
                        my_fighter.stop_block()
            else:
                my_fighter.move(move_dir)
                if want_jump:
                    my_fighter.jump()
                if want_atk:
                    my_fighter.attack()
                if want_block:
                    my_fighter.start_block()
                else:
                    my_fighter.stop_block()
                if want_pickup:
                    _handle_pickup(my_fighter, arena)

        # -- Push my input to Firebase -----------------------------------------
        if frame_count % 2 == 0 and not game_over:
            inp_data = {
                "ts": _time.time(),
                "move": move_dir,
                "face": face_dir,
                "jump": want_jump,
                "attack": want_atk,
                "block": want_block,
                "pickup": want_pickup,
                "role": my_role,
                "vx": my_fighter.vx,
                "vy": my_fighter.vy,
            }
            slot = my_slot
            threading.Thread(target=db.push_input,
                             args=(room_code, slot, inp_data), daemon=True).start()
        else:
            inp_data = {
                "ts": _time.time(),
                "move": move_dir,
                "face": face_dir,
                "jump": want_jump,
                "attack": want_atk,
                "block": want_block,
                "pickup": want_pickup,
                "role": my_role,
            }

        # -- HOST: read remote inputs + run game logic -------------------------
        if is_host:
            with _sync_lock:
                ri = dict(_remote_input)

            if is_4p:
                # Merge inputs for Team A & Team B
                a_m = inp_data if my_slot == "a_left" else ri.get("a_left", {})
                a_a = inp_data if my_slot == "a_right" else ri.get("a_right", {})
                b_m = inp_data if my_slot == "b_left" else ri.get("b_left", {})
                b_a = inp_data if my_slot == "b_right" else ri.get("b_right", {})

                # Apply to Team A (p1)
                if isinstance(a_m, dict):
                    p1.move_input(a_m.get("move", 0))
                    if a_m.get("jump"):   p1.jump()
                    if a_m.get("pickup"): _handle_pickup(p1, arena)
                if isinstance(a_a, dict):
                    p1.face_input(a_a.get("face", 0))
                    if a_a.get("attack"): p1.attack()
                    if a_a.get("block"):  p1.start_block()
                    else:                 p1.stop_block()

                # Apply to Team B (p2)
                if isinstance(b_m, dict):
                    p2.move_input(b_m.get("move", 0))
                    if b_m.get("jump"):   p2.jump()
                    if b_m.get("pickup"): _handle_pickup(p2, arena)
                if isinstance(b_a, dict):
                    p2.face_input(b_a.get("face", 0))
                    if b_a.get("attack"): p2.attack()
                    if b_a.get("block"):  p2.start_block()
                    else:                 p2.stop_block()

                # Coordination check
                if isinstance(a_m, dict) and isinstance(a_a, dict):
                    am_dir = a_m.get("move", 0)
                    aa_dir = a_a.get("face", 0)
                    if am_dir != 0 and am_dir == aa_dir:
                        p1.coord_bonus = 2.0
                        p1.coord_glow = True

                if isinstance(b_m, dict) and isinstance(b_a, dict):
                    bm_dir = b_m.get("move", 0)
                    ba_dir = b_a.get("face", 0)
                    if bm_dir != 0 and bm_dir == ba_dir:
                        p2.coord_bonus = 2.0
                        p2.coord_glow = True

            else:
                # 2P Mode: Apply remote player's input
                other_slot = None
                for s in ri:
                    if s != my_slot:
                        other_slot = s
                        break
                if other_slot and ri.get(other_slot) and isinstance(ri[other_slot], dict):
                    rd = ri[other_slot]
                    other_fighter.move(rd.get("move", 0))
                    if rd.get("jump"):   other_fighter.jump()
                    if rd.get("attack"): other_fighter.attack()
                    if rd.get("block"):  other_fighter.start_block()
                    else:                other_fighter.stop_block()
                    if rd.get("pickup"):
                        _handle_pickup(other_fighter, arena)

            if not game_over:
                # Physics update
                surfaces = arena.get_collide_surfaces()
                walls    = arena.get_walls_only()
                p1.update(dt, surfaces, walls)
                p2.update(dt, surfaces, walls)
                arena.update(dt)
                particles.update(dt)
                shake.update(dt)

                # -- Combat: melee attacks -------------------------------------
                for atk, dfn in [(p1, p2), (p2, p1)]:
                    if atk.is_attacking and atk.attack_anim > 0.12:
                        info = atk.weapon_info
                        if not info.get("projectile"):
                            dist = abs(atk.center_x - dfn.center_x)
                            dy   = abs(atk.center_y - dfn.center_y)
                            if dist < info["range"] and dy < 70:
                                direction = 1 if atk.x < dfn.x else -1
                                dmg = info["damage"]
                                has_coord = is_4p and atk.coord_bonus > 0
                                if has_coord:
                                    dmg = max(1, int(dmg * 1.15))
                                dfn.take_damage(dmg, direction, info["knockback"])
                                atk.damage_dealt += dmg
                                # Effects
                                hx = int((atk.center_x + dfn.center_x) / 2)
                                hy = int((atk.center_y + dfn.center_y) / 2)
                                burst_col = (255, 215, 0) if has_coord else (255, 200, 80)
                                particles.emit_burst(hx, hy, burst_col, 10 if has_coord else 8, 140 if has_coord else 120, 3, 0.35)
                                if dfn.blocking:
                                    dmg_numbers.append(DamageNumber(0, dfn.center_x, dfn.y - 20,
                                                                     (100, 160, 255), False, "BLOCKED!"))
                                    particles.emit_sparks(hx, hy, (100, 160, 255), 5, 100)
                                else:
                                    dmg_numbers.append(DamageNumber(dmg, dfn.center_x,
                                                                     dfn.y - 20, GOLD if has_coord else HP_R))
                                    shake.trigger(8 if has_coord else 6, 0.14 if has_coord else 0.12)
                                    hitstop.trigger(4 if has_coord else 3)
                                # Damage crates in range
                                for w in arena.walls:
                                    if not w.get("destructible") or w["hp"] <= 0:
                                        continue
                                    wx_c = w["x"] + w["w"] / 2
                                    wy_c = w["y"] + w["h"] / 2
                                    if abs(atk.center_x - wx_c) < info["range"] and abs(atk.center_y - wy_c) < 60:
                                        arena.damage_wall(w, dmg)
                                        particles.emit_sparks(int(wx_c), int(wy_c), (180, 140, 80), 4, 80)
                                atk.attack_anim = 0.12  # prevent multi-hit

                        elif info.get("projectile"):
                            # Bow: spawn arrow with owner_team
                            arena.spawn_arrow(atk.center_x + atk.facing * 20,
                                              atk.center_y, atk.facing, atk.player_id, atk.team)
                            atk.attack_anim = 0.12

                # -- Arrow hits ------------------------------------------------
                for arrow in arena.arrows:
                    for dfn in [p1, p2]:
                        if arrow.hits_fighter(dfn):
                            direction = 1 if arrow.vx > 0 else -1
                            dfn.take_damage(arrow.damage, direction, arrow.knockback)
                            dmg_numbers.append(DamageNumber(arrow.damage, dfn.center_x,
                                                             dfn.y - 20, (160, 200, 120)))
                            particles.emit_burst(int(dfn.center_x), int(dfn.center_y),
                                                 (160, 200, 120), 6, 100, 2, 0.3)
                            arrow.alive = False
                            break

                # -- Check win condition ---------------------------------------
                if p1.hp <= 0:
                    game_over = True; winner = "TEAM B" if is_4p else "P2"
                    particles.emit_burst(int(p1.center_x), int(p1.center_y),
                                         (255, 100, 50), 30, 250, 5, 0.8, 100)
                    shake.trigger(15, 0.4)
                elif p2.hp <= 0:
                    game_over = True; winner = "TEAM A" if is_4p else "P1"
                    particles.emit_burst(int(p2.center_x), int(p2.center_y),
                                         (255, 100, 50), 30, 250, 5, 0.8, 100)
                    shake.trigger(15, 0.4)

            # Push game state to Firebase
            if frame_count % SYNC_RATE == 0:
                gs = {
                    "ts": _time.time(),
                    "p1": p1.to_dict(), "p2": p2.to_dict(),
                    "arena": arena.to_dict(),
                    "game_over": game_over, "winner": winner,
                }
                with _sync_lock:
                    _remote_state.clear()
                    _remote_state.update(gs)

        else:
            # -- CLIENT: apply remote game state with interpolation ------------
            with _sync_lock:
                gs = dict(_remote_state)
            if gs:
                gs_ts = gs.get("ts", 0)
                new_snapshot = gs_ts > _last_gs_ts
                if new_snapshot:
                    _last_gs_ts = gs_ts

                # Extract raw dicts from the snapshot
                p1d = gs.get("p1") or {}
                p2d = gs.get("p2") or {}

                # Update interpolation targets (positions + velocities)
                if new_snapshot:
                    _p1_target["x"]  = p1d.get("x", _p1_target["x"])
                    _p1_target["y"]  = p1d.get("y", _p1_target["y"])
                    _p1_target["vx"] = p1d.get("vx", 0)
                    _p1_target["vy"] = p1d.get("vy", 0)
                    _p2_target["x"]  = p2d.get("x", _p2_target["x"])
                    _p2_target["y"]  = p2d.get("y", _p2_target["y"])
                    _p2_target["vx"] = p2d.get("vx", 0)
                    _p2_target["vy"] = p2d.get("vy", 0)

                # Apply discrete (non-position) state immediately
                # -- these values look fine when snapped instantly --
                for f, fd in [(p1, p1d), (p2, p2d)]:
                    if fd:
                        f.hp           = fd.get("hp", f.hp)
                        f.weapon       = fd.get("weapon", f.weapon)
                        f.facing       = fd.get("facing", f.facing)
                        f.on_ground    = fd.get("on_ground", f.on_ground)
                        f.is_attacking = fd.get("attacking", f.is_attacking)
                        f.attack_anim  = fd.get("attack_anim", f.attack_anim)
                        f.blocking     = fd.get("blocking", f.blocking)
                        f.hit_flash    = fd.get("hit_flash", f.hit_flash)
                        f.damage_dealt = fd.get("damage_dealt", f.damage_dealt)
                        f.team         = fd.get("team", f.team)
                        f.coord_bonus  = fd.get("coord_bonus", f.coord_bonus)
                        f.coord_glow   = f.coord_bonus > 0

                arena.from_dict(gs.get("arena"))
                game_over = gs.get("game_over", False)
                winner = gs.get("winner", "")

            # Smoothly interpolate positions towards targets
            t = min(1.0, _interp_speed * dt)  # lerp factor this frame
            for f, tgt in [(p1, _p1_target), (p2, _p2_target)]:
                # Predict target a little ahead using velocity for smoother feel
                pred_x = tgt["x"] + tgt["vx"] * dt
                pred_y = tgt["y"] + tgt["vy"] * dt
                # Lerp towards predicted position
                f.x += (pred_x - f.x) * t
                f.y += (pred_y - f.y) * t
                f.vx = tgt["vx"]
                f.vy = tgt["vy"]
                # If very close to target, snap to avoid floating point drift
                if abs(f.x - tgt["x"]) < 0.5:
                    f.x = tgt["x"]
                if abs(f.y - tgt["y"]) < 0.5:
                    f.y = tgt["y"]

            # Client still updates visuals
            arena.update(dt)
            particles.update(dt)
            shake.update(dt)

            # Client: handle own weapon pickup locally (sends via input)
            if want_pickup:
                _handle_pickup(my_fighter, arena)

        # Update damage numbers
        for d in dmg_numbers: d.update(dt)
        dmg_numbers[:] = [d for d in dmg_numbers if d.alive]
        ctrl_fade = max(0, ctrl_fade - dt)

        # Check weapon pickup hint
        pickup_hint = ""
        for wp in arena.weapon_pickups:
            if wp.active and wp.collides_with(my_fighter):
                pickup_hint = f"Press E to pick up {wp.weapon.upper()}"
                break

        # ======================================================================
        #  RENDERING
        # ======================================================================
        cx, cy = shake.offset_x, shake.offset_y

        # Arena (bg, platforms, walls, weapons, arrows)
        arena.draw(screen, gf("Segoe UI", 10, True), cx, cy)

        # Fighters
        draw_fighter(screen, p1, cx, cy)
        draw_fighter(screen, p2, cx, cy)

        # "YOU" arrow over my fighter
        you_cx = int(my_fighter.center_x + cx)
        you_y  = int(my_fighter.y - 40 + cy + math.sin(game_time * 3) * 4)
        pygame.draw.polygon(screen, GOLD,
                            [(you_cx, you_y + 10), (you_cx - 7, you_y), (you_cx + 7, you_y)])
        you_text = f"YOU ({my_role.upper()})" if is_4p else "YOU"
        yt = gf("Segoe UI", 11, True).render(you_text, True, GOLD)
        screen.blit(yt, (you_cx - yt.get_width() // 2, you_y - 16))

        # Particles + damage numbers
        particles.draw(screen, cx, cy)
        fonts_cache = {}
        for d in dmg_numbers:
            d.draw(screen, fonts_cache, cx, cy)

        # -- HUD --------------------------------------------------------------
        hud = pygame.Surface((W_WIDTH, 62 if is_4p else 55), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 180))
        screen.blit(hud, (0, 0))

        bar_w = 350
        # P1 / Team A HP (left)
        p1_title = "TEAM A" if is_4p else "P1"
        p1_lbl = gf("Segoe UI", 15, True).render(f"{p1_title}  {WEAPON_DEFS.get(p1.weapon, {}).get('name', 'Fists')}", True, P1_COL)
        screen.blit(p1_lbl, (12, 4))
        draw_hp_bar(screen, 12, 24, bar_w, 18, max(0, p1.hp), 100, hp_color(max(0, p1.hp)))
        hp1_t = gf("Segoe UI", 12, True).render(f"{max(0, p1.hp)} HP", True, WHITE)
        screen.blit(hp1_t, (16, 26))
        if is_4p and p1.coord_bonus > 0:
            sync_a = gf("Segoe UI", 10, True).render(f"SYNC BOOST +15% ({p1.coord_bonus:.1f}s)", True, GOLD)
            screen.blit(sync_a, (16, 44))

        # P2 / Team B HP (right)
        p2_title = "TEAM B" if is_4p else "P2"
        p2_lbl = gf("Segoe UI", 15, True).render(f"{WEAPON_DEFS.get(p2.weapon, {}).get('name', 'Fists')}  {p2_title}", True, P2_COL)
        screen.blit(p2_lbl, (W_WIDTH - 12 - p2_lbl.get_width(), 4))
        draw_hp_bar(screen, W_WIDTH - 12 - bar_w, 24, bar_w, 18, max(0, p2.hp), 100,
                    hp_color(max(0, p2.hp)), right=True)
        hp2_t = gf("Segoe UI", 12, True).render(f"{max(0, p2.hp)} HP", True, WHITE)
        screen.blit(hp2_t, (W_WIDTH - 16 - hp2_t.get_width(), 26))
        if is_4p and p2.coord_bonus > 0:
            sync_b = gf("Segoe UI", 10, True).render(f"SYNC BOOST +15% ({p2.coord_bonus:.1f}s)", True, GOLD)
            screen.blit(sync_b, (W_WIDTH - 16 - sync_b.get_width(), 44))

        # VS
        vs = gf("Segoe UI", 20, True).render("VS", True, GOLD)
        screen.blit(vs, (W_WIDTH // 2 - vs.get_width() // 2, 12))

        # Weapon pickup hint
        if pickup_hint:
            ht = gf("Segoe UI", 16, True).render(pickup_hint, True, GOLD)
            bg2 = pygame.Surface((ht.get_width() + 20, ht.get_height() + 10), pygame.SRCALPHA)
            bg2.fill((0, 0, 0, 160))
            screen.blit(bg2, (W_WIDTH // 2 - bg2.get_width() // 2, GROUND_Y + 25))
            screen.blit(ht, (W_WIDTH // 2 - ht.get_width() // 2, GROUND_Y + 30))

        # Controls hint (fades out)
        if ctrl_fade > 0:
            alpha = min(1.0, ctrl_fade)
            if is_4p:
                if my_role == "mover":
                    c_line = "A/D = Move (Legs)    W/SPACE = Jump    E = Pickup Weapon    [Partner aims & attacks!]"
                else:
                    c_line = "A/D = Aim Face    J = Attack    K = Block (hold)    [Partner moves & jumps!]"
                lines = [
                    c_line,
                    f"Room: {room_code} | {my_id} | {'HOST' if is_host else 'CLIENT'} | Both press same direction for +15% SYNC BOOST",
                ]
            else:
                lines = [
                    "A/D = Move    W/SPACE = Jump    J = Attack    K = Block (hold)    E = Pick up weapon",
                    f"Room: {room_code} | You are {my_id} | {'HOST' if is_host else 'CLIENT'}",
                ]
            for i, line in enumerate(lines):
                lt = gf("Segoe UI", 12).render(line, True, GRAY)
                lt.set_alpha(int(255 * alpha))
                screen.blit(lt, (W_WIDTH // 2 - lt.get_width() // 2, GROUND_Y + 55 + i * 18))

        # Footer
        fps_t = gf("Segoe UI", 10).render(f"FPS:{int(clock.get_fps())}  Room:{room_code}", True, DIM)
        screen.blit(fps_t, (W_WIDTH - fps_t.get_width() - 8, W_HEIGHT - 14))

        # -- Game over overlay -------------------------------------------------
        if game_over:
            ov = pygame.Surface((W_WIDTH, W_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            screen.blit(ov, (0, 0))

            wc = P1_COL if (winner in ("P1", "TEAM A")) else P2_COL
            wt2 = gf("Segoe UI", 60, True).render(f"{winner} WINS!", True, wc)
            screen.blit(wt2, (W_WIDTH // 2 - wt2.get_width() // 2, W_HEIGHT // 2 - 80))

            # Stats
            t1_name = "Team A" if is_4p else "P1"
            t2_name = "Team B" if is_4p else "P2"
            stats_lines = [
                f"{t1_name} damage dealt: {p1.damage_dealt}     {t2_name} damage dealt: {p2.damage_dealt}",
                f"{t1_name} final HP: {max(0, p1.hp)}     {t2_name} final HP: {max(0, p2.hp)}",
            ]
            for i, sl in enumerate(stats_lines):
                st = gf("Segoe UI", 16).render(sl, True, GRAY)
                screen.blit(st, (W_WIDTH // 2 - st.get_width() // 2, W_HEIGHT // 2 + 20 + i * 28))

            if is_host and int(game_time * 2) % 2 == 0:
                rt = gf("Segoe UI", 18, True).render("Press ENTER to play again", True, GOLD)
                screen.blit(rt, (W_WIDTH // 2 - rt.get_width() // 2, W_HEIGHT // 2 + 100))
            elif not is_host:
                wt3 = gf("Segoe UI", 14).render("Waiting for host to restart...", True, GRAY)
                screen.blit(wt3, (W_WIDTH // 2 - wt3.get_width() // 2, W_HEIGHT // 2 + 100))

        pygame.display.flip()
        await asyncio.sleep(0)

    _sync_running = False
    try:
        db.set_status(room_code, "over")
    except Exception:
        pass
    pygame.quit()
    sys.exit()


def _handle_pickup(fighter, arena):
    """Try to pick up a weapon near the fighter, or drop current."""
    for wp in arena.weapon_pickups:
        if wp.active and wp.collides_with(fighter):
            old = fighter.drop_weapon()
            fighter.pickup_weapon(wp.weapon)
            wp.collect()
            # If they had a weapon, drop it where the pickup was
            if old and old != "fists":
                # Find a pickup that's inactive and of that type, or just mark it
                pass
            return
    # No pickup nearby -- drop current weapon
    fighter.drop_weapon()


if __name__ == "__main__":
    asyncio.run(main())
