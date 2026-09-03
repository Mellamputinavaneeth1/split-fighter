"""
firebase_db.py -- Firebase Realtime Database REST wrapper for Split Fighter.

Uses only the built-in `requests` library (no Firebase SDK needed).
Firebase is used as the shared "room database" so players on different
devices can find each other using only a 4-digit room code.

DB Structure:
    /rooms/{code}/
        code        : "4821"
        status      : "lobby" | "starting" | "fight" | "over"
        created_at  : float (unix timestamp)
        host_slot   : "a_left" (which slot the host took)
        slots       : {a_left: "P1", a_right: "", b_left: "", b_right: ""}
        game_state  : { ... full serialised game state ... }
        inputs      : {a_left: {...}, a_right: {...}, b_left: {...}, b_right: {...}}
"""

import requests
import json
import time
import threading


# --- Load config -------------------------------------------------------------
import os as _os

_CONFIG_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "config.json")


def _read_config() -> dict:
    """Read config.json, return empty dict if missing/invalid."""
    try:
        with open(_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_config(cfg: dict):
    """Write config to config.json."""
    with open(_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def _validate_url(url: str) -> bool:
    """Quick check: can we reach the Firebase DB?"""
    try:
        r = requests.get(f"{url}/.json", params={"shallow": "true"}, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def load_firebase_url() -> str:
    """
    Read firebase_url from config.json.
    Safe for both desktop and browser WebAssembly.
    """
    default_url = "https://split-fighter-default-rtdb.firebaseio.com"
    cfg = _read_config()
    url = cfg.get("firebase_url", "").rstrip("/")

    if url and "YOUR-PROJECT" not in url and url.startswith("https://"):
        return url

    # Fallback to default without blocking browser
    return default_url


# --- FirebaseDB ---------------------------------------------------------------
class FirebaseDB:
    """
    Thin REST wrapper around Firebase Realtime Database.
    All methods are synchronous (blocking HTTP calls).
    Use the *_async variants or call from a thread for non-blocking usage.
    """

    TIMEOUT = 5.0   # seconds per HTTP request

    def __init__(self):
        self.base_url = load_firebase_url()
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # -- Internal helpers -----------------------------------------------------
    def _url(self, *parts) -> str:
        path = "/".join(str(p) for p in parts)
        return f"{self.base_url}/{path}.json"

    def _get(self, *parts):
        try:
            r = self._session.get(self._url(*parts), timeout=self.TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        return None

    def _put(self, data, *parts) -> bool:
        try:
            r = self._session.put(self._url(*parts), data=json.dumps(data),
                                  timeout=self.TIMEOUT)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _patch(self, data, *parts) -> bool:
        try:
            r = self._session.patch(self._url(*parts), data=json.dumps(data),
                                    timeout=self.TIMEOUT)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _delete(self, *parts) -> bool:
        try:
            r = self._session.delete(self._url(*parts), timeout=self.TIMEOUT)
            return r.status_code in (200, 204)
        except requests.RequestException:
            return False

    # -- Room CRUD -------------------------------------------------------------
    def create_room(self, code: str, host_slot: str, mode: str = "2p") -> bool:
        """Create a new room. Returns False if code already exists."""
        existing = self._get("rooms", code)
        if existing and existing.get("status") in ("lobby", "fight"):
            return False   # code collision -- caller should retry with new code

        if mode == "4p":
            slot_dict = {"a_left": "", "a_right": "", "b_left": "", "b_right": ""}
            input_dict = {"a_left": None, "a_right": None, "b_left": None, "b_right": None}
        else:
            slot_dict = {"a_left": "", "b_left": ""}
            input_dict = {"a_left": None, "b_left": None}

        room_data = {
            "code":        code,
            "status":      "lobby",
            "created_at":  time.time(),
            "host_slot":   host_slot,
            "mode":        mode,
            "slots":       slot_dict,
            "game_state": None,
            "inputs":      input_dict,
        }
        return self._put(room_data, "rooms", code)

    def get_room(self, code: str) -> dict | None:
        """Fetch full room data. Returns None if not found."""
        data = self._get("rooms", code)
        if data and isinstance(data, dict) and "code" in data:
            return data
        return None

    def get_room_mode(self, code: str) -> str:
        """Return room mode: '2p' or '4p'."""
        room = self._get("rooms", code)
        if room and isinstance(room, dict):
            return room.get("mode", "2p")
        return "2p"

    def room_exists(self, code: str) -> bool:
        room = self.get_room(code)
        return room is not None and room.get("status") in ("lobby", "fight")

    def claim_slot(self, code: str, slot: str, player_name: str) -> bool:
        """
        Try to claim a slot. Returns False if slot is already taken.
        Uses a read-then-write (optimistic); good enough for lobby phase.
        """
        room = self.get_room(code)
        if not room:
            return False
        current = room.get("slots", {}).get(slot, "")
        if current and current != player_name:
            return False   # already taken by someone else
        return self._patch({f"slots/{slot}": player_name}, "rooms", code)

    def release_slot(self, code: str, slot: str) -> bool:
        return self._patch({f"slots/{slot}": ""}, "rooms", code)

    def get_slots(self, code: str) -> dict:
        data = self._get("rooms", code, "slots")
        return data if isinstance(data, dict) else {}

    def set_status(self, code: str, status: str) -> bool:
        return self._patch({"status": status}, "rooms", code)

    def delete_room(self, code: str) -> bool:
        return self._delete("rooms", code)

    # -- Game state sync ------------------------------------------------------
    def push_game_state(self, code: str, state: dict) -> bool:
        """Host writes the authoritative game state."""
        return self._put(state, "rooms", code, "game_state")

    def pull_game_state(self, code: str) -> dict | None:
        """Clients read the latest game state."""
        return self._get("rooms", code, "game_state")

    # -- Input sync -----------------------------------------------------------
    def push_input(self, code: str, slot: str, input_data: dict) -> bool:
        """Each player writes their current inputs."""
        return self._put(input_data, "rooms", code, "inputs", slot)

    def pull_inputs(self, code: str) -> dict:
        """Host reads all player inputs."""
        data = self._get("rooms", code, "inputs")
        return data if isinstance(data, dict) else {}


# --- AsyncPoller -------------------------------------------------------------
class AsyncPoller:
    """
    Background thread that polls Firebase at a fixed rate
    and stores the latest value for non-blocking reads.

    Usage:
        poller = AsyncPoller(db, "rooms/4821/slots", interval=0.5)
        poller.start()
        ...
        latest = poller.value   # always the most recent fetched value
        poller.stop()
    """

    def __init__(self, db: FirebaseDB, path_parts: list, interval: float = 0.5):
        self._db        = db
        self._parts     = path_parts
        self._interval  = interval
        self.value      = None
        self._running   = False
        self._thread    = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self.value = self._db._get(*self._parts)
            except Exception:
                pass
            time.sleep(self._interval)


# --- Serialisation helpers ----------------------------------------------------
def serialise_fighter(f) -> dict:
    """Convert a Fighter object to a JSON-safe dict."""
    return {
        "x":             f.x,
        "y":             f.y,
        "hp":            max(0, f.hp),
        "stamina":       max(0, f.stamina),
        "coordination":  max(0, f.coordination),
        "left_action":   f.left_action,
        "right_action":  f.right_action,
        "active_buffs":  dict(f.active_buffs),
        "hit_flash":     f.hit_flash_timer,
        # stats
        "damage_dealt":        f.damage_dealt,
        "combos_landed":       f.combos_landed,
        "blocks_done":         f.blocks_done,
        "dodges_done":         f.dodges_done,
        "powerups_collected":  f.powerups_collected,
    }


def apply_fighter_state(f, data: dict):
    """Apply a state dict back onto a Fighter object."""
    if not data:
        return
    f.x             = data.get("x", f.x)
    f.y             = data.get("y", f.y)
    f.hp            = data.get("hp", f.hp)
    f.stamina       = data.get("stamina", f.stamina)
    f.coordination  = data.get("coordination", f.coordination)
    f.left_action   = data.get("left_action", f.left_action)
    f.right_action  = data.get("right_action", f.right_action)
    f.active_buffs  = data.get("active_buffs", f.active_buffs) or {}
    f.hit_flash_timer = data.get("hit_flash", 0.0)
    f.damage_dealt        = data.get("damage_dealt", 0)
    f.combos_landed       = data.get("combos_landed", 0)
    f.blocks_done         = data.get("blocks_done", 0)
    f.dodges_done         = data.get("dodges_done", 0)
    f.powerups_collected  = data.get("powerups_collected", 0)


def serialise_powerups(pu_list) -> list:
    out = []
    for pu in pu_list:
        if pu.alive:
            out.append({"x": pu.x, "y": pu.y, "kind": pu.kind, "age": pu.age})
    return out


def serialise_game_state(team_a, team_b, round_timer, round_num,
                          a_wins, b_wins, state_id, pu_list,
                          quest_a, quest_b, dmg_events=None) -> dict:
    """Build the full game state dict for Firebase."""
    def ser_quests(qs):
        return [{"desc": q.desc, "progress": q.progress,
                 "target": q.target, "completed": q.completed} for q in qs]

    return {
        "ts":          time.time(),
        "state":       state_id,       # 0=fight, 1=round_end, 2=match_over
        "round_timer": round_timer,
        "round_num":   round_num,
        "a_wins":      a_wins,
        "b_wins":      b_wins,
        "team_a":      serialise_fighter(team_a),
        "team_b":      serialise_fighter(team_b),
        "powerups":    serialise_powerups(pu_list),
        "quest_a":     ser_quests(quest_a),
        "quest_b":     ser_quests(quest_b),
        "dmg_events":  dmg_events or [],
    }


def serialise_input(left_action, right_action,
                    left_move, right_move) -> dict:
    return {
        "ts":           time.time(),
        "left_action":  left_action,
        "right_action": right_action,
        "left_move":    left_move,
        "right_move":   right_move,
    }
