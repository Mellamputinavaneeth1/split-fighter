# 🥊 Split Fighter — 1v1 Arena Brawl (Networked Multiplayer)

A 1v1 real-time networked arena fighting game built with **Python**, **Pygame**, and **Google Firebase Realtime Database**.

---

## 🎮 Features

- **Cross-Device Cloud Multiplayer**: Real-time matchmaking with a 4-digit room code powered by Firebase REST API.
- **Platformer Arena Combat**: Platforms, destructible crates, stone obstacles, jump physics, and gravity.
- **Weapons System**:
  - 👊 **Fists**: Default melee attack.
  - ⚔️ **Sword**: Medium range, fast arc swing.
  - 🪓 **Axe**: Heavy melee with massive knockback.
  - 🛡️ **Shield**: Enhanced guard blocking up to 80% damage.
  - 🏹 **Bow**: Long-range projectile shooting.
- **Visual Effects**: Particle bursts, hit sparks, screen shake, hit-stop impact frames, and dynamic floating damage numbers.
- **Host-Authoritative Sync**: Host processes physics and authoritative combat state, pushing updates (~15-20 FPS) while receiving player inputs.
- **Academic AI Architecture**: Includes Minimax & Alpha-Beta Pruning decision engines (`ai.py`) with state evaluation.

---

## 🕹️ Controls

| Action | Key(s) |
|---|---|
| **Move Left / Right** | `A` / `D` |
| **Jump** | `W` or `SPACE` |
| **Attack (Punch / Weapon Swing / Shoot)** | `J` |
| **Block / Guard** | `K` (Hold) |
| **Pick Up / Drop Weapon** | `E` |
| **Restart Match (Host)** | `ENTER` (after game over) |
| **Quit** | `ESC` |

---

## 🚀 Quick Start & Installation

### Option 1: One-Click Launcher (Windows)
Double-click `PLAY.bat` in the project root. It will automatically verify Python, install dependencies, and launch the game.

### Option 2: Manual Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<YOUR-USERNAME>/split-fighter.git
   cd split-fighter
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Firebase**:
   - Create a free Firebase project at [Firebase Console](https://console.firebase.google.com).
   - Go to **Build** → **Realtime Database** → **Create Database** (Start in **Test Mode**).
   - Copy your database URL and edit `config.json`:
     ```json
     {
         "firebase_url": "https://your-project-default-rtdb.firebaseio.com"
     }
     ```

4. **Launch the Game**:
   ```bash
   python main.py
   ```

---

## 🌐 How Multiplayer Works

1. **Player 1 (Host)**:
   - Selects **CREATE ROOM** → Picks **PLAYER 1 (Red)** slot.
   - Gets a unique **4-digit room code** (e.g., `4821`).
   - Shares the code with Player 2.
2. **Player 2 (Client)**:
   - Launches game → Selects **JOIN ROOM** → Enters the 4-digit code.
   - Selects **PLAYER 2 (Blue)** slot.
3. **Fight**:
   - Host presses `SPACE` to start the arena match!

---

## 📁 Project Structure

```
split_fighter/
├── main.py           # Main game loop, rendering, combat resolution & network sync
├── fighter.py        # Player physics (gravity, jumps, collisions, weapons, HP)
├── arena.py          # Arena map layout, platforms, crates, weapon pickups, arrows
├── effects.py        # Particle system, screen shake, hit-stop, damage numbers
├── lobby.py          # Interactive UI menu & Firebase matchmaking lobby
├── firebase_db.py    # Firebase REST API wrapper & state serialisation
├── ai.py             # Minimax algorithm & Alpha-Beta Pruning implementation
├── config.json       # Firebase Realtime Database connection endpoint
├── requirements.txt  # Python package dependencies
├── PLAY.bat          # Windows one-click automated setup & launcher
└── README.md         # Documentation
```

---

## 🧠 Algorithms Implemented

1. **Minimax Decision Rule**: Generates and evaluates future combat states (`ai.py`).
2. **Alpha-Beta Pruning**: Reduces branching factor in the state evaluation tree.
3. **State Evaluation Heuristic**: Weighted heuristic scoring HP advantage, stamina balance, and combat spacing.
4. **Swarm Simulation**: Particle velocity, decay, and gravity simulations for explosive hit impacts.
5. **Fuzzy Logic & Resolution**: Fuzzy HP threshold indicators and conflict resolution for simultaneous attack/block timings.

---

## 📜 License
MIT License
