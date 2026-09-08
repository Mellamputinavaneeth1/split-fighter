# 🥊 Split Fighter — 2D Competitive & Cooperative Arena Brawl

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Pygame](https://img.shields.io/badge/Pygame-2.6+-yellow.svg?logo=pygame&logoColor=white)](https://pygame.org)
[![WebAssembly](https://img.shields.io/badge/WebAssembly-Pygbag-654FF0.svg?logo=webassembly&logoColor=white)](https://pygame-web.github.io)
[![Firebase](https://img.shields.io/badge/Firebase-Realtime_DB-FFA611.svg?logo=firebase&logoColor=white)](https://firebase.google.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A cross-platform 2D competitive platform fighting game built with **Python**, **Pygame**, and **Firebase Realtime Database**, deployable as a native desktop application and directly in the browser via **WebAssembly (Pygbag)**.

Features **1v1 VS Minimax AI**, **1v1 Online Multiplayer**, and a unique **2v2 Cooperative Split-Control Mode** where two teammates jointly pilot a single fighter.

---

## 🎮 Game Modes

1. **🤖 1v1 Practice Mode (VS Minimax AI)**:
   * Play offline against a tactical AI bot powered by **Minimax Search**, **Alpha-Beta Pruning**, and a **Weighted Multi-Factor Evaluation Heuristic**.
   * Features distinct visual character models: **Titan-X Cyber-Mech Robot** (AI) vs. **Crimson Brawler** (Player).

2. **🌐 1v1 Online Cloud Multiplayer**:
   * Instant cross-device matchmaking using a 4-digit room code powered by Firebase REST API.
   * Host-authoritative synchronization with **Dead Reckoning** and **Linear Velocity Interpolation (LERP)** for smooth, lag-free action.

3. **🤝 2v2 Cooperative "Split-Control" Brawl**:
   * Two players on each team control different subsystems of the same fighter:
     * **Mover**: Handles horizontal navigation, jumping, and weapon acquisition.
     * **Attacker**: Handles facing orientation, weapon attacks, and defensive shielding.
   * **Directional Synergy Mechanic**: Moving and facing in the same direction triggers a **+15% Coordination Damage Boost** with golden aura effects!

---

## 🕹️ Controls Guide

### Standard 1v1 Mode (Local & Online)

| Action | Key(s) |
|---|---|
| **Move Left / Right** | `A` / `D` |
| **Jump** | `W` or `SPACE` |
| **Attack (Punch / Weapon Swing / Shoot)** | `J` |
| **Block / Guard (Shield)** | `K` (Hold) |
| **Pick Up / Drop Weapon** | `E` |
| **Restart Match (Host)** | `ENTER` (after game over) |
| **Quit** | `ESC` |

### 2v2 Cooperative Split-Control Mode

| Team Role | Key(s) | Description |
|---|---|---|
| **🏃 MOVER** | `A` / `D` | Run Left / Right |
| | `W` or `SPACE` | Jump onto platforms |
| | `E` | Grab / Swap weapons |
| **⚔️ ATTACKER** | `A` / `D` | Change facing direction |
| | `J` | Attack (Strike / Shoot) |
| | `K` (Hold) | Raise Shield / Guard |

---

## 🎨 Procedural Vector Graphics & Visual Design

To guarantee zero asset loading errors, instant start times, and flawless cross-platform WebAssembly performance, all game assets are rendered using procedural vector mathematics:

* ⚔️ **Vector Weapon Pickups**:
  * **Sword**: Double-edged steel blade with central fuller groove, gold crossguard, wrapped grip, and pommel over a glowing sapphire pedestal.
  * **Axe**: Wood-grain haft with twin curved battleaxe blades and gold binding rings over an ember pedestal.
  * **Bow**: Curved recurve wood bow, taut string, notched arrow with golden tip over a forest emerald pedestal.
  * **Shield**: Steel heater shield with cyan border trim and glowing gold cross emblem over a sky-blue pedestal.
* 🌆 **Cyberpunk Arena Skyline**:
  * Atmospheric deep night sky with harmonic twinkling starfield.
  * Layered skyscraper silhouettes with randomized window matrices and pulsing red rooftop hazard beacons.
* 🚧 **Industrial Arena Architecture**:
  * Segmented steel ground with diagonal caution hazard stripes (`///`) and a luminous neon cyan boundary line.
  * Dark-chassis floating platforms equipped with vent gratings and glowing blue thruster nodes underneath.
  * Reinforced military cargo crates with iron corner brackets, gold rivets, and dynamic splinter crack damage.
* 🤖 **Distinct Character Models**:
  * **Titan-X Cyber Bot**: Angular metallic chassis, antenna with blinking red signal LED, animated cyan Cylon scanning visor, and pulsing Arc Reactor chest core.
  * **Crimson Brawler**: Martial arts Gi tunic, black belt obi, focused combat eyes, and dynamic fluttering headband ribbons.

---

## 🧠 Complete Inventory of Algorithms & Mathematical Models

Split Fighter implements academic algorithms across artificial intelligence, kinematics, networking, and rendering:

### 1. Artificial Intelligence & Decision Making (`ai.py`)

* **Minimax Search Algorithm (Game Theory / Zero-Sum Adversarial Tree Search)**:
  * Evaluates multi-turn combat projections using a depth-limited game tree.
  * Utilizes isolated `MockFighter` state clones to simulate candidate actions (Approach, Retreat, Jump, Attack, Block, Pickup) without mutating the live game state.
* **Alpha-Beta Pruning Optimization ($\\alpha\\text{-}\\beta$ Pruning)**:
  * Eliminates subtrees that cannot influence the final decision ($\\beta \\le \\alpha$).
  * Compresses decision complexity from $O(b^d)$ to approximately $O(b^{d/2})$, executing within the $16\\text{ ms}$ frame budget.
* **Weighted Multi-Factor State Evaluation Heuristic**:
  * Evaluates non-terminal horizon states factoring:
    1. **Health Differential**: $(\\text{HP}_{\\text{AI}} - \\text{HP}_{\\text{Opponent}}) \\times 8.0$ with $\\pm 9999.0$ terminal KO clamps.
    2. **Weapon Tier Valuation**: Weighted advantage hierarchy ($\\text{Fists: 0} < \\text{Shield: 10} < \\text{Sword: 20} < \\text{Bow: 22} < \\text{Axe: 25}$).
    3. **Spatial Spacing & Range Heuristic**: Rewards projectile standoff distance ($180\\text{--}480\\text{ px}$) vs. melee strike zones ($< hit\\_range$).
    4. **Defensive Reflex Utility**: Evaluates active defense when the enemy attacks within strike range.
    5. **Resource Seeking**: Distance-decay heuristic attracting unarmed bots to the nearest weapon pickup.
* **Simple Reflex Agent (Condition-Action Production Rules)**:
  * Executes every frame ($60\\text{ Hz}$) for instantaneous reactions:
    * **Ballistic Threat Dodging**: Detects incoming arrow trajectory vectors and triggers an evasive jump or shield.
    * **Reactive Guard**: Automatically raises block when opponent swings in close range.
* **Biological Deliberation Delay & Jitter**:
  * Prevents superhuman frame-perfect bot play by introducing realistic human-like reaction latency ($0.10\\text{s} + \\mathcal{U}(0.01, 0.04)\\text{s}$).

### 2. Kinematics & Physics Simulation (`fighter.py`, `arena.py`)

* **Semi-Implicit Euler Numerical Integration**:
  * Simulates 2D kinematics with gravity, drag, velocity clamping, and terminal velocity:
    $$v_y(t + \\Delta t) = \\min(v_y(t) + g \\cdot \\Delta t, v_{\\text{max}})$$
    $$y(t + \\Delta t) = y(t) + v_y(t + \\Delta t) \\cdot \\Delta t$$
* **Axis-Aligned Bounding Box (AABB) Collision Detection & Separation**:
  * Discrete collision detection and positional separation against solid walls and terrain boundaries.
* **One-Way Platform Passing & Swept Edge Detection**:
  * Allows fighters to jump through platforms from underneath, landing on top only when falling downward ($v_y \\ge 0$).
* **Impulse & Exponential Knockback Decay**:
  * Directional momentum transfer on impact decaying over time ($0.15\\text{s}$), reduced by $70\\%$ when guarding.
* **Continuous Ray-Box Ballistic Trajectory**:
  * Team-aware projectile travel ($650\\text{ px/s}$) detecting intersections with obstacles and opposing fighters.

### 3. Networking, Synchronization & State Management (`firebase_db.py`, `main.py`)

* **Host-Authoritative Client-Server Architecture**:
  * The room host acts as the authoritative simulation server, while clients stream inputs and receive synchronized world snapshots.
* **Dead Reckoning with Linear Velocity Interpolation (LERP)**:
  * Eliminates remote player stutter and network latency jitter:
    $$\\vec{p}_{\\text{pred}} = \\vec{p}_{\\text{target}} + \\vec{v}_{\\text{target}} \\cdot \\Delta t$$
    $$\\vec{p}(t + \\Delta t) = \\vec{p}(t) + (\\vec{p}_{\\text{pred}} - \\vec{p}(t)) \\cdot \\min(1.0, \\lambda \\cdot \\Delta t) \\quad (\\lambda = 18.0)$$
* **Input Latching (Edge-to-Level Conversion)**:
  * Locks one-shot inputs (Jump, Attack, Pickup) until consumed by a network sync tick, preventing dropped inputs across variable tick rates.
* **Optimistic Concurrency Control**:
  * Non-destructive slot claiming and lobby management via atomic HTTP PATCH requests.
* **Asynchronous Non-Blocking Polling Daemon (`AsyncPoller`)**:
  * Threaded I/O background polling keeping the main Pygame rendering thread at a locked $60\\text{ FPS}$.

### 4. Game Feel, Visual Effects & Rendering (`effects.py`, `arena.py`, `main.py`)

* **Exponential Ghost HP Decay Algorithm**:
  * Dual-layer health representation where the primary HP drops instantly and a secondary ghost bar catches up smoothly:
    $$HP_{\\text{ghost}}(t + \\Delta t) = \\max\\left(HP, \\; HP_{\\text{ghost}} - \\max(20.0, \\; (HP_{\\text{ghost}} - HP) \\cdot 4.5) \\cdot \\Delta t\\right)$$
* **Camera Trauma Shake with Linear Decay (`ScreenShake`)**:
  * Generates random 2D camera viewport offsets scaled by decaying trauma intensity.
* **Hit-Stop (Frame-Freeze Impact Algorithm)**:
  * Temporarily halts physics updates for 3–4 frames upon heavy hits to deliver tactile physical weight.
* **Euler Particle System with Attenuation**:
  * Multi-emitter particle engine handling hit sparks, blood/energy bursts, and collect rings with alpha and radius decay.

---

## 🚀 Installation & Running

### Option 1: Browser WebAssembly (Zero Install)
Play directly in any modern browser via GitHub Pages:
👉 **[Play Split Fighter Online](https://mellamputinavaneeth1.github.io/split-fighter/)**

---

### Option 2: Windows Automated Launcher
1. Clone the repository:
   ```bash
   git clone https://github.com/Mellamputinavaneeth1/split-fighter.git
   cd split-fighter
   ```
2. Double-click **`PLAY.bat`** (automatically verifies dependencies and starts the game).

---

### Option 3: Manual Python Setup
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the game**:
   ```bash
   python main.py
   ```

---

## 🛠️ Building & Compiling

### Build Standalone Windows Executable (`.exe`)
To package the game into a single standalone folder with no Python requirement:
```bash
# Double-click BUILD_EXE.bat or run:
pyinstaller --noconfirm --onedir --windowed --name "SplitFighter" --add-data "config.json;." main.py
```
The output binary will be located in `dist/SplitFighter/SplitFighter.exe`.

### Build WebAssembly Bundle (Pygbag)
To compile the game for browser deployment:
```bash
python -m pygbag --build main.py
```
The resulting web bundle is output to `build/web/`.

---

## 📁 Repository Structure

```
split_fighter/
├── main.py           # Game loop, HUD rendering, combat resolution & network sync
├── fighter.py        # Player physics, state machine, weapons, AABB collisions, ghost HP
├── arena.py          # Procedural map, cyberpunk skyline, crates, platforms, projectiles
├── ai.py             # Minimax algorithm, Alpha-Beta Pruning & reflex decision engine
├── effects.py        # Particle system, screen shake, hit-stop, damage numbers
├── lobby.py          # Matchmaking menu, room creation, slot selection UI
├── firebase_db.py    # Firebase REST API client, async poller, state serialization
├── config.json       # Firebase Realtime Database endpoint configuration
├── requirements.txt  # Python package dependencies
├── PLAY.bat          # Windows one-click automated setup & launcher
├── BUILD_EXE.bat     # PyInstaller standalone Windows compilation script
├── SplitFighter.spec # PyInstaller build specification
└── build/web/        # Compiled WebAssembly build for GitHub Pages
```

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
