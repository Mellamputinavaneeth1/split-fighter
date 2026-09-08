"""
ai.py -- AI Decision Engine for Split Fighter
Implements:
  1. Exp 6: Minimax Decision Algorithm
  2. Exp 7: Alpha-Beta Pruning Optimization
  3. Exp 1: Simple Reflex Reactions (Guard/Jump/Pickup)
  4. Exp 12: Fuzzy / Weighted State Evaluation Heuristic
"""

import math
import random
from fighter import Fighter, WEAPON_DEFS

# --- Action Tokens -----------------------------------------------------------
ACT_IDLE     = 0
ACT_APPROACH = 1
ACT_RETREAT  = 2
ACT_JUMP     = 3
ACT_ATTACK   = 4
ACT_BLOCK    = 5
ACT_PICKUP   = 6

ALL_ACTIONS = [ACT_IDLE, ACT_APPROACH, ACT_RETREAT, ACT_JUMP, ACT_ATTACK, ACT_BLOCK, ACT_PICKUP]

# Weapon tier values for evaluation
WEAPON_TIER = {
    "fists":  0,
    "shield": 10,
    "sword":  20,
    "axe":    25,
    "bow":    22,
}


# --- Exp 12: Weighted State Evaluation Heuristic -----------------------------
def evaluate_state(ai_f, opp_f, arena=None) -> float:
    """
    Evaluates combat state from the perspective of the AI.
    Higher score means AI has a stronger advantage.
    """
    score = 0.0

    # 1. HP Advantage (Weighted heavily)
    score += (ai_f.hp - opp_f.hp) * 8.0

    # Critical survival penalty
    if ai_f.hp <= 0:
        return -9999.0
    if opp_f.hp <= 0:
        return 9999.0

    # 2. Weapon Advantage
    ai_w_val  = WEAPON_TIER.get(ai_f.weapon, 0)
    opp_w_val = WEAPON_TIER.get(opp_f.weapon, 0)
    score += (ai_w_val - opp_w_val) * 1.5

    # 3. Spatial Spacing & Range Evaluation
    dist = abs(ai_f.center_x - opp_f.center_x)
    dy   = abs(ai_f.center_y - opp_f.center_y)
    info = ai_f.weapon_info

    if info.get("projectile"):
        # Bow prefers standoff distance (200 - 450 px)
        if 180 <= dist <= 480 and dy < 80:
            score += 35.0
        elif dist < 120:
            score -= 25.0   # too close for bow
    else:
        # Melee weapon prefers striking range
        hit_range = info["range"]
        if dist <= hit_range and dy < 60:
            score += 30.0   # in strike zone
            if ai_f.is_attacking:
                score += 25.0
        elif dist < hit_range + 80:
            score += 10.0   # closing in
        else:
            score -= (dist * 0.05)  # slight penalty for being far

    # 4. Defensive Reflex Evaluation
    # If opponent is currently attacking and close, blocking is rewarded
    if opp_f.is_attacking and dist < opp_f.weapon_info["range"] + 20:
        if ai_f.blocking:
            score += 40.0   # successful guard
        else:
            score -= 30.0   # vulnerable to incoming hit

    # 5. Weapon seeking reward if holding fists
    if arena and ai_f.weapon == "fists" and hasattr(arena, "weapon_pickups"):
        for wp in arena.weapon_pickups:
            if wp.active:
                wp_dist = abs(ai_f.center_x - wp.x)
                score += max(0, (300 - wp_dist) * 0.08)
                break

    return score


# --- Simulation Model for Minimax --------------------------------------------
class MockFighter:
    """Lightweight clone of fighter state for tree search projections."""
    def __init__(self, f):
        self.x            = f.x
        self.y            = f.y
        self.hp           = f.hp
        self.weapon       = f.weapon
        self.facing       = f.facing
        self.is_attacking = f.is_attacking
        self.blocking     = f.blocking
        self.on_ground    = f.on_ground
        self.WIDTH        = f.WIDTH
        self.HEIGHT       = f.HEIGHT

    @property
    def center_x(self):
        return self.x + self.WIDTH / 2

    @property
    def center_y(self):
        return self.y + self.HEIGHT / 2

    @property
    def weapon_info(self):
        return WEAPON_DEFS.get(self.weapon, WEAPON_DEFS["fists"])


def simulate_action(agent: MockFighter, opponent: MockFighter, action: int):
    """Applies an action to the mock state for forward projection."""
    info = agent.weapon_info
    dist = abs(agent.center_x - opponent.center_x)

    if action == ACT_APPROACH:
        step = 16.0
        agent.facing = 1 if agent.x < opponent.x else -1
        agent.x += agent.facing * step
    elif action == ACT_RETREAT:
        step = 16.0
        direction = -1 if agent.x < opponent.x else 1
        agent.x += direction * step
    elif action == ACT_JUMP:
        agent.y -= 30.0
        agent.on_ground = False
    elif action == ACT_ATTACK:
        agent.is_attacking = True
        agent.blocking = False
        # If in range and opponent not blocking, deal simulated damage
        if dist < info["range"]:
            dmg = info["damage"]
            if opponent.blocking:
                dmg = max(1, int(dmg * 0.4))
            opponent.hp -= dmg
    elif action == ACT_BLOCK:
        agent.blocking = True
        agent.is_attacking = False
    elif action == ACT_IDLE:
        agent.blocking = False
        agent.is_attacking = False


# --- Exp 6 & 7: Minimax Algorithm with Alpha-Beta Pruning --------------------
def minimax(ai_mock: MockFighter, opp_mock: MockFighter, depth: int,
            is_maximizing: bool, alpha: float, beta: float, arena=None) -> float:
    """
    Minimax search with Alpha-Beta Pruning (Exp 6 & Exp 7).
    Recursively projects game tree to find the optimal counter-action.
    """
    # Base case: terminal depth or someone KO'd
    if depth == 0 or ai_mock.hp <= 0 or opp_mock.hp <= 0:
        return evaluate_state(ai_mock, opp_mock, arena)

    candidate_actions = [ACT_APPROACH, ACT_ATTACK, ACT_BLOCK, ACT_JUMP, ACT_RETREAT]

    if is_maximizing:
        max_eval = float('-inf')
        for act in candidate_actions:
            # Clone states
            next_ai  = MockFighter(ai_mock)
            next_opp = MockFighter(opp_mock)
            simulate_action(next_ai, next_opp, act)

            eval_score = minimax(next_ai, next_opp, depth - 1, False, alpha, beta, arena)
            max_eval = max(max_eval, eval_score)
            alpha    = max(alpha, eval_score)

            # Alpha-Beta Pruning Cutoff
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for act in candidate_actions:
            # Opponent tries to minimize AI's score
            next_ai  = MockFighter(ai_mock)
            next_opp = MockFighter(opp_mock)
            simulate_action(next_opp, next_ai, act)

            eval_score = minimax(next_ai, next_opp, depth - 1, True, alpha, beta, arena)
            min_eval = min(min_eval, eval_score)
            beta     = min(beta, eval_score)

            # Alpha-Beta Pruning Cutoff
            if beta <= alpha:
                break
        return min_eval


# --- Exp 1: AIAgent with Reflex Actuation & Pathfinding -----------------------
class AIAgent:
    """
    Real-time AI Controller for Split Fighter.
    Combines:
      - Minimax + Alpha-Beta for high-level tactical decisions
      - Simple reflex triggers for fast reaction (arrow dodging, weapon pickup, jump)
    """

    def __init__(self, depth: int = 2, reaction_delay: float = 0.10):
        self.depth           = depth
        self.reaction_delay  = reaction_delay
        self.timer           = 0.0

        # Current control outputs
        self.move_dir        = 0
        self.want_jump       = False
        self.want_atk        = False
        self.want_block      = False
        self.want_pickup     = False

    def update(self, ai_f: Fighter, opp_f: Fighter, arena, dt: float):
        """Called every frame. Updates reflexes and runs Minimax on timer tick."""
        self.timer -= dt

        # Reset per-frame pulse flags
        self.want_jump   = False
        self.want_atk    = False
        self.want_pickup = False

        # Periodic tactical deliberation via Minimax & Alpha-Beta
        if self.timer <= 0:
            self.timer = self.reaction_delay + random.uniform(0.01, 0.04)
            self._deliberate(ai_f, opp_f, arena)

        # Fast frame-by-frame reflexes (Exp 1: Simple Reflex Agent)
        self._apply_reflexes(ai_f, opp_f, arena)

        # Actuate fighter with decided controls
        ai_f.move(self.move_dir)
        if self.want_jump:
            ai_f.jump()
        if self.want_atk:
            ai_f.attack()
        if self.want_block:
            ai_f.start_block()
        else:
            ai_f.stop_block()
        if self.want_pickup:
            self._handle_pickup(ai_f, arena)

    def _deliberate(self, ai_f: Fighter, opp_f: Fighter, arena):
        """Runs Minimax with Alpha-Beta to choose the highest-scoring action."""
        best_score  = float('-inf')
        best_action = ACT_APPROACH
        alpha       = float('-inf')
        beta        = float('inf')

        # Evaluate all possible candidate actions
        for act in ALL_ACTIONS:
            next_ai  = MockFighter(ai_f)
            next_opp = MockFighter(opp_f)
            simulate_action(next_ai, next_opp, act)

            score = minimax(next_ai, next_opp, self.depth - 1, False, alpha, beta, arena)
            if score > best_score:
                best_score  = score
                best_action = act
            alpha = max(alpha, best_score)

        # Map high-level action to control signals
        dist = opp_f.center_x - ai_f.center_x
        face = 1 if dist > 0 else -1

        if best_action == ACT_APPROACH:
            self.move_dir   = face
            self.want_block = False
        elif best_action == ACT_RETREAT:
            self.move_dir   = -face
            self.want_block = False
        elif best_action == ACT_ATTACK:
            self.move_dir   = 0
            self.want_atk   = True
            self.want_block = False
        elif best_action == ACT_BLOCK:
            self.move_dir   = 0
            self.want_block = True
        elif best_action == ACT_JUMP:
            self.want_jump  = True
        elif best_action == ACT_PICKUP:
            self.want_pickup = True
        else:
            self.move_dir   = 0
            self.want_block = False

    def _apply_reflexes(self, ai_f: Fighter, opp_f: Fighter, arena):
        """Immediate reactionary reflexes that run every single frame."""
        dist = abs(ai_f.center_x - opp_f.center_x)
        dy   = opp_f.y - ai_f.y

        # 1. Reflex: Pickup weapon if standing over one and current weapon is fists
        if arena and hasattr(arena, "weapon_pickups"):
            for wp in arena.weapon_pickups:
                if wp.active and wp.collides_with(ai_f):
                    if ai_f.weapon == "fists" or WEAPON_TIER.get(wp.weapon, 0) > WEAPON_TIER.get(ai_f.weapon, 0):
                        self.want_pickup = True
                        break

        # 2. Reflex: Navigate towards weapon if holding fists
        if ai_f.weapon == "fists" and arena and hasattr(arena, "weapon_pickups"):
            nearest_wp = None
            min_d = 9999
            for wp in arena.weapon_pickups:
                if wp.active:
                    d = abs(ai_f.center_x - wp.x)
                    if d < min_d:
                        min_d = d
                        nearest_wp = wp
            if nearest_wp and min_d > 20:
                self.move_dir = 1 if nearest_wp.x > ai_f.center_x else -1
                if nearest_wp.y < ai_f.y - 30 and ai_f.on_ground:
                    self.want_jump = True

        # 3. Reflex: Jump over obstacles or jump up to higher platforms
        if opp_f.y < ai_f.y - 40 and dist < 160 and ai_f.on_ground:
            self.want_jump = True

        # 4. Reflex: Reactive Shield when opponent attacks in range
        if opp_f.is_attacking and dist < opp_f.weapon_info["range"] + 25:
            self.want_block = True
            self.want_atk   = False

        # 5. Reflex: Attack if in weapon range and not blocking
        info = ai_f.weapon_info
        if not self.want_block and ai_f.attack_timer <= 0:
            if info.get("projectile"):
                if dist < 450 and abs(dy) < 60:
                    self.want_atk = True
            else:
                if dist < info["range"] and abs(dy) < 55:
                    self.want_atk = True

        # 6. Reflex: Dodge or block incoming arrows
        if arena and hasattr(arena, "arrows"):
            for arrow in arena.arrows:
                if arrow.alive and getattr(arrow, "owner_team", None) != ai_f.team:
                    arrow_dist = arrow.x - ai_f.center_x
                    approaching = (arrow.vx > 0 and arrow_dist < 0) or (arrow.vx < 0 and arrow_dist > 0)
                    if approaching and abs(arrow_dist) < 140 and abs(arrow.y - ai_f.center_y) < 40:
                        if ai_f.on_ground and random.random() < 0.6:
                            self.want_jump = True
                        else:
                            self.want_block = True

    def _handle_pickup(self, fighter, arena):
        """Picks up a weapon if colliding with a pickup."""
        if not arena or not hasattr(arena, "weapon_pickups"):
            return
        for wp in arena.weapon_pickups:
            if wp.active and wp.collides_with(fighter):
                fighter.pickup_weapon(wp.weapon)
                wp.collect()
                return
