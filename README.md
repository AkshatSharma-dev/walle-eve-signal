# WALL-E and EVE's Signal — Interactive Program

1. Project Overview

This project implements an autonomous agent that explores a simulated environment to locate EVE. WALL-E starts with an initial signal and must discover hidden clues through scanning, update its beliefs, and manage limited battery and mission time.

The agent makes decisions based on its observations instead of directly accessing EVE's hidden location.

2. Environment Design

The environment is a two-dimensional grid containing WALL-E, a hidden target (EVE), obstacles, a charging station, and hidden clues.

The system consists of two main components:

Environment: Stores the map, hidden locations, resources, and action costs. It executes actions and returns observations.

Agent: Chooses whether to move, scan, recharge, or stop. It uses the initial signal and discovered clues to guide its search.

The agent and environment interact repeatedly until EVE is found or the mission ends. Each action and its outcome are recorded for analysis.

3. Configuration Format

The program collects mission settings through terminal inputs. These include:

Map dimensions and starting coordinates

EVE's hidden location and charging station

Signal direction, strength, and timestamp

Obstacles and clue locations

Battery budget, time limit, and action costs

Coordinates use the (x, y) format, starting from (0, 0) at the top-left corner.

The mission configuration is saved as mission_config_used.json. The program also uses JSON to generate the final mission report.

Note: EVE's location is stored privately in the environment. The agent can discover clues only by scanning their locations.

4. Run
1. Open the folder in VS Code.
2. Open Terminal → New Terminal.
3. Run `python main.py` (or `py main.py` on Windows).

## What you can enter
Map dimensions, WALL-E start, charger position, EVE's hidden position, obstacle coordinates, signal direction/strength/timestamp, battery and time budgets, action costs, and clue positions/names/hints/target regions.

Coordinates are `x,y`, with the top-left cell at `0,0`.

## Output
The program shows each decision, the reason, action result, battery/time remaining, and a simple map. It creates `mission_report.json` (including the action trace) and `mission_config_used.json` (the entered settings).

## Design note
The environment stores EVE's real location and clue locations privately. The agent only receives clue information after scanning a clue's cell. The initial signal biases its search scores. This is an educational baseline; confidence is illustrative, and signal timestamps are recorded but do not yet implement signal decay.
