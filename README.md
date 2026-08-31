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

## 🚀 How to Play

### Option 1: Standalone Executable (No Python Required)
1. Download the game ZIP from [GitHub Releases](https://github.com/Mellamputinavaneeth1/split-fighter/releases).
2. Extract the folder and double-click **`SplitFighter.exe`** to play!

---

### Option 2: One-Click Launcher (Windows with Python)
1. Clone or download the repository:
   ```bash
   git clone https://github.com/Mellamputinavaneeth1/split-fighter.git
   cd split-fighter
   ```
2. Double-click **`PLAY.bat`**. It will automatically verify dependencies and launch the game.

---

### Option 3: Manual Python Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Firebase (Optional)**:
   - The game connects to the default Firebase endpoint out of the box.
   - To use your own Firebase database, edit `config.json`:
     ```json
     {
         "firebase_url": "https://your-project-default-rtdb.firebaseio.com"
     }
     ```

3. **Launch the Game**:
   ```bash
   python main.py
   ```

---

## 🌐 How Multiplayer Works

1. **Player 1 (Host)**:
   - Selects **CREATE ROOM** → Picks **PLAYER 1 (Red)** slot.
   - Receives a unique **4-digit room code** (e.g., `4821`).
   - Shares the code with Player 2.
2. **Player 2 (Client)**:
   - Launches the game → Selects **JOIN ROOM** → Enters the 4-digit code.
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
├── BUILD_EXE.bat     # Automated standalone Windows .exe compiler (PyInstaller)
└── README.md         # Documentation
```

---

## 🛠️ Building Standalone `.exe`

To package the game into a standalone Windows binary:
```bash
# Double-click BUILD_EXE.bat or run:
pyinstaller --noconfirm --onedir --windowed --name "SplitFighter" --add-data "config.json;." main.py
```
The output binary will be created in `dist/SplitFighter/SplitFighter.exe`.

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
