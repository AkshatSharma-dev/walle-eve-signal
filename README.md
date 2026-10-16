# WALL-E and EVE's Signal — Interactive Program

## Run
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
