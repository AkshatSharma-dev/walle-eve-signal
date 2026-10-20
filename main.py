import json
import math
from collections import deque
from pathlib import Path

DIRS = {
    "N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
    "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)
}

def integer(prompt, minimum=0, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
            if value < minimum:
                print(f"Enter a value greater than or equal to {minimum}.")
                continue
            return value
        except ValueError:
            print("Enter a whole number.")

def number(prompt, minimum=0.0, maximum=1.0, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = float(raw)
            if not minimum <= value <= maximum:
                print(f"Enter a value from {minimum} to {maximum}.")
                continue
            return value
        except ValueError:
            print("Enter a number, such as 0.8.")

def position(prompt, width, height, forbidden=None):
    forbidden = forbidden or set()
    while True:
        raw = input(
            f"{prompt} (x,y; x=0..{width - 1}, y=0..{height - 1}): "
        ).strip()
        try:
            values = [int(part.strip()) for part in raw.split(",")]
            if len(values) != 2:
                raise ValueError
            point = tuple(values)
            if not (0 <= point[0] < width and 0 <= point[1] < height):
                print("Coordinate is outside the map.")
                continue
            if point in forbidden:
                print("That cell is already occupied. Choose another.")
                continue
            return point
        except ValueError:
            print("Use x,y format, for example 2,3.")

def yesno(prompt, default="y"):
    while True:
        raw = input(f"{prompt} (y/n) [{default}]: ").strip().lower() or default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Enter y or n.")

def get_config():
    print("\n" + "=" * 64)
    print(" WALL-E AND EVE'S SIGNAL — MISSION CONFIGURATION")
    print("=" * 64)
    print("Coordinates use x,y. The top-left cell is (0,0).")
    print("EVE and undiscovered clues are hidden from the agent.")

    width = integer("Map width", minimum=2, default=6)
    height = integer("Map height", minimum=2, default=5)

    print("\n-- Starting positions --")
    start = position("WALL-E starting position", width, height)
    charger = position("Charging station position", width, height)
    eve = position("EVE's hidden position", width, height, {start})

    print("\n-- Obstacles --")
    obstacle_count = integer("Number of obstacles", minimum=0, default=0)
    obstacles = set()
    reserved = {start, charger, eve}
    for index in range(obstacle_count):
        point = position(
            f"Obstacle {index + 1}", width, height,
            forbidden=obstacles | reserved
        )
        obstacles.add(point)

    print("\n-- Initial signal --")
    while True:
        direction = input("Signal direction (N, NE, E, SE, S, SW, W, NW): ").strip().upper()
        if direction in DIRS:
            break
        print("Choose N, NE, E, SE, S, SW, W, or NW.")

    strength = number("Signal strength (0 to 1)", 0.0, 1.0, 0.8)
    timestamp = input("Signal timestamp/label [mission-start]: ").strip() or "mission-start"

    print("\n-- Resources and action costs --")
    battery_max = integer("Maximum battery units", minimum=3, default=30)
    time_budget = integer("Mission time budget (actions)", minimum=3, default=45)
    move_cost = integer("Battery cost per move", minimum=1, default=1)
    scan_cost = integer("Battery cost per scan", minimum=1, default=2)
    recharge_time = integer("Time steps for a full recharge", minimum=1, default=3)

    print("\n-- Hidden clues --")
    clue_count = integer("Number of clues", minimum=0, default=2)
    clues = []
    reserved_clue_cells = set(reserved) | obstacles
    for index in range(clue_count):
        print(f"\nClue {index + 1}:")
        point = position(
            "Clue location", width, height,
            forbidden=reserved_clue_cells | {tuple(c["position"]) for c in clues}
        )
        name = input(f"Clue name [Clue {index + 1}]: ").strip() or f"Clue {index + 1}"
        hint = input("Hint text [EVE may be nearby]: ").strip() or "EVE may be nearby"

        print("Enter the rectangular region this clue points toward.")
        min_x = integer("Minimum x", 0, max(0, min(width - 1, eve[0] - 1)))
        min_y = integer("Minimum y", 0, max(0, min(height - 1, eve[1] - 1)))
        max_x = integer("Maximum x", min_x, width - 1)
        max_y = integer("Maximum y", min_y, height - 1)

        clues.append({
            "position": point,
            "name": name,
            "hint": hint,
            "region": (min_x, min_y, max_x, max_y)
        })

    return {
        "width": width,
        "height": height,
        "start": start,
        "charger": charger,
        "eve": eve,
        "obstacles": obstacles,
        "signal": {
            "direction": direction,
            "strength": strength,
            "timestamp": timestamp
        },
        "battery_max": battery_max,
        "time": time_budget,
        "move_cost": move_cost,
        "scan_cost": scan_cost,
        "recharge_time": recharge_time,
        "clues": clues
    }

class Environment:
    def __init__(self, config):
        self.c = config
        self.pos = config["start"]
        self.battery = config["battery_max"]
        self.time = config["time"]
        self.finished = False
        self.found = False
        self.visited = {self.pos}
        self.scanned = set()
        self.found_clues = []

        self._eve = config["eve"]
        self._clues = {clue["position"]: clue for clue in config["clues"]}

        self.reported_clues = set()

    def observe(self):
        clue_observation = None

        if self.pos in self.scanned and self.pos in self._clues:
            hidden_clue = self._clues[self.pos]
            if self.pos not in self.reported_clues:
                clue_observation = {
                    "name": hidden_clue["name"],
                    "hint": hidden_clue["hint"],
                    "region": hidden_clue["region"]
                }
                self.reported_clues.add(self.pos)

        return {
            "position": self.pos,
            "battery": self.battery,
            "battery_max": self.c["battery_max"],
            "time": self.time,
            "at_charger": self.pos == self.c["charger"],
            "eve_found": self.found,
            "clue": clue_observation
        }

    def step(self, action):
        if self.finished:
            return "Mission already finished."

        kind = action["type"]
        message = ""

        if kind == "move":
            dx, dy = DIRS[action["direction"]]
            target = (self.pos[0] + dx, self.pos[1] + dy)

            if self.battery < self.c["move_cost"] or self.time < 1:
                message = "Move rejected: insufficient battery or time."
            elif not (0 <= target[0] < self.c["width"] and 0 <= target[1] < self.c["height"]):
                message = "Map boundary reached; position unchanged."
            elif target in self.c["obstacles"]:
                self.battery -= self.c["move_cost"]
                self.time -= 1
                message = f"Obstacle encountered at {target}."
            else:
                old = self.pos
                self.pos = target
                self.visited.add(target)
                self.battery -= self.c["move_cost"]
                self.time -= 1
                message = f"Moved from {old} to {target}."

        elif kind == "scan":
            if self.battery < self.c["scan_cost"] or self.time < 1:
                message = "Scan rejected: insufficient battery or time."
            else:
                self.battery -= self.c["scan_cost"]
                self.time -= 1
                self.scanned.add(self.pos)

                if self.pos == self._eve:
                    self.found = True
                    self.finished = True
                    message = "EVE FOUND! Mission successful."
                elif self.pos in self._clues:
                    clue = self._clues[self.pos]
                    if not any(item["position"] == self.pos for item in self.found_clues):
                        self.found_clues.append({
                            "position": self.pos,
                            "name": clue["name"],
                            "hint": clue["hint"],
                            "region": clue["region"]
                        })
                    message = f"Clue found: {clue['name']}. Hint: {clue['hint']}"
                else:
                    message = "Scan complete; no clue detected."

        elif kind == "recharge":
            if self.pos != self.c["charger"]:
                message = "Recharge failed: not at the charging station."
            elif self.time < self.c["recharge_time"]:
                message = "Recharge failed: insufficient time."
            else:
                self.battery = self.c["battery_max"]
                self.time -= self.c["recharge_time"]
                message = "Battery fully recharged."

        elif kind == "return":
            if self.pos == self.c["charger"]:
                self.finished = True
                message = "Returned safely to the charging station."
            else:
                message = "Return requested, but WALL-E is not at the charger."

        elif kind == "stop":
            self.finished = True
            message = "Agent stopped."

        else:
            message = f"Unknown action: {kind}"
            self.finished = True

        if self.battery <= 0 or self.time <= 0:
            self.finished = True
            if not self.found:
                message += " Resources exhausted; mission ended."

        return message

class Agent:
    def __init__(self, config):
        self.c = config
        self.pos = config["start"]
        self.visited = set()
        self.scanned = set()
        self.trace = []
        self.belief = {}

        dx, dy = DIRS[config["signal"]["direction"]]
        sx, sy = config["start"]
        strength = config["signal"]["strength"]

        for y in range(config["height"]):
            for x in range(config["width"]):
                point = (x, y)
                if point == self.pos or point in config["obstacles"]:
                    continue
                forward = (x - sx) * dx + (y - sy) * dy
                side = abs((x - sx) * dy - (y - sy) * dx)
                self.belief[point] = max(0.05, 1 + max(0, forward) * strength - side * 0.15)

    def update(self, observation):
        self.pos = observation["position"]
        self.visited.add(self.pos)

        clue = observation.get("clue")
        if clue:
            min_x, min_y, max_x, max_y = clue["region"]
            for point in self.belief:
                inside = min_x <= point[0] <= max_x and min_y <= point[1] <= max_y
                self.belief[point] *= 4.0 if inside else 0.2

    def bfs_path(self, start, goal, blocked):
        if start == goal:
            return []

        queue = deque([(start, [])])
        seen = {start}

        while queue:
            point, path = queue.popleft()

            for direction, (dx, dy) in DIRS.items():
                nxt = (point[0] + dx, point[1] + dy)

                if not (0 <= nxt[0] < self.c["width"] and 0 <= nxt[1] < self.c["height"]):
                    continue
                if nxt in blocked or nxt in seen:
                    continue

                new_path = path + [direction]
                if nxt == goal:
                    return new_path

                seen.add(nxt)
                queue.append((nxt, new_path))

        return None

    def choose(self, observation, known_obstacles):
        self.update(observation)
        position = self.pos
        battery = observation["battery"]
        battery_max = observation["battery_max"]
        time_left = observation["time"]

        if observation["eve_found"]:
            return {"type": "stop"}, "EVE has already been found."

        move_cost = self.c["move_cost"]
        scan_cost = self.c["scan_cost"]
        charger = self.c["charger"]

        if position == charger and battery < battery_max * 0.65:
            if time_left >= self.c["recharge_time"] + 1:
                return {"type": "recharge"}, "Battery is below 65%; recharge at the station."
            return {"type": "stop"}, "Battery is low and there is not enough time to recharge safely."

        path_home = self.bfs_path(position, charger, known_obstacles)
        if path_home is None and position != charger:
            return {"type": "stop"}, "No known safe route to the charger; stop rather than risk a blind route."

        steps_home = len(path_home) if path_home is not None else 0
        battery_to_home = steps_home * move_cost
        time_to_home = steps_home

        battery_reserve = battery_to_home + scan_cost
        time_reserve = time_to_home + 1

        must_return = (
            battery <= battery_reserve
            or time_left <= time_reserve
        )

        if must_return:
            if position == charger:
                if battery < battery_max and time_left >= self.c["recharge_time"] + 1:
                    return {"type": "recharge"}, "At the charger with limited resources; recharge."
                return {"type": "return"}, "At the charger; end the mission safely."
            if path_home:
                return (
                    {"type": "move", "direction": path_home[0]},
                    f"Return early: home needs about {battery_to_home} battery units and {time_to_home} moves."
                )
            return {"type": "stop"}, "Insufficient resources or no known route home."

        if position not in self.scanned:
            self.scanned.add(position)
            return {"type": "scan"}, "Scan this cell for EVE or a hidden clue."

        candidates = []
        for point, score in self.belief.items():
            if point in self.visited or point in known_obstacles:
                continue
            path = self.bfs_path(position, point, known_obstacles)
            if path:
                adjusted_score = score / (1 + len(path) * 0.25)
                candidates.append((adjusted_score, point, path))

        if candidates:
            _, target, path = max(candidates, key=lambda item: item[0])
            return (
                {"type": "move", "direction": path[0]},
                f"Explore promising unvisited cell {target}."
            )

        if position != charger:
            path = self.bfs_path(position, charger, known_obstacles)
            if path:
                return {"type": "move", "direction": path[0]}, "No unexplored target remains; return to base."

        return {"type": "stop"}, "No further safe action is available."

def draw_map(config, environment):
    clue_positions = {item["position"] for item in environment.found_clues}
    print("Map: W=WALL-E, E=EVE found, #=obstacle, C=charger, ?=found clue, ·=visited, .=unknown")

    for y in range(config["height"]):
        row = []
        for x in range(config["width"]):
            point = (x, y)
            if point == environment.pos:
                char = "E" if environment.found else "W"
            elif point in config["obstacles"]:
                char = "#"
            elif point == config["charger"]:
                char = "C"
            elif point in clue_positions:
                char = "?"
            elif point in environment.visited:
                char = "·"
            else:
                char = "."
            row.append(char)
        print(" ".join(row))

def json_safe_config(config):
    return {
        "map": {"width": config["width"], "height": config["height"]},
        "start": list(config["start"]),
        "charger": list(config["charger"]),
        "eve_hidden": list(config["eve"]),
        "obstacles": [list(point) for point in sorted(config["obstacles"])],
        "signal": config["signal"],
        "resources": {"battery": config["battery_max"], "time": config["time"]},
        "costs": {
            "move": config["move_cost"],
            "scan": config["scan_cost"],
            "recharge_time": config["recharge_time"]
        },
        "clues": [
            {
                "position": list(clue["position"]),
                "name": clue["name"],
                "hint": clue["hint"],
                "target_region": list(clue["region"])
            }
            for clue in config["clues"]
        ]
    }

def main():
    config = get_config()

    print("\n-- Mission summary --")
    print(f"Map: {config['width']}x{config['height']} | Start: {config['start']} | Charger: {config['charger']}")
    print(f"Signal: {config['signal']} | Battery: {config['battery_max']} | Time: {config['time']}")
    print(f"Obstacles: {len(config['obstacles'])} | Clues: {len(config['clues'])}")

    if not yesno("Start mission?", "y"):
        print("Mission cancelled.")
        return

    environment = Environment(config)
    agent = Agent(config)
    observation = environment.observe()
    known_obstacles = set()

    max_steps = config["time"] + 10

    while not environment.finished and len(agent.trace) < max_steps:
        action, reason = agent.choose(observation, known_obstacles)
        result = environment.step(action)
        observation = environment.observe()

        if action["type"] == "move" and "Obstacle encountered" in result:
            dx, dy = DIRS[action["direction"]]
            attempted = (agent.pos[0] + dx, agent.pos[1] + dy)
            known_obstacles.add(attempted)

        agent.trace.append({
            "step": len(agent.trace) + 1,
            "position": list(observation["position"]),
            "action": action,
            "reason": reason,
            "result": result,
            "battery": observation["battery"],
            "time_left": observation["time"]
        })

        print(f"\nStep {len(agent.trace)} | Position: {observation['position']} | Action: {action}")
        print("Reason:", reason)
        print("Result:", result)
        print(f"Battery: {observation['battery']} | Time left: {observation['time']}")
        draw_map(config, environment)

    report = {
        "mission_success": environment.found,
        "eve_location": list(environment.pos) if environment.found else None,
        "clues_found": [
            {
                "position": list(clue["position"]),
                "name": clue["name"],
                "hint": clue["hint"],
                "target_region": list(clue["region"])
            }
            for clue in environment.found_clues
        ],
        "visited_cells": [list(point) for point in sorted(environment.visited)],
        "final_position": list(environment.pos),
        "battery_remaining": environment.battery,
        "time_remaining": environment.time,
        "confidence": 1.0 if environment.found else min(0.9, 0.2 + 0.15 * len(environment.found_clues)),
        "recommended_next_step": (
            "Report EVE's location; mission complete."
            if environment.found
            else "Increase time/battery or improve the search strategy."
        ),
        "signal": config["signal"],
        "trace": agent.trace
    }

    Path("mission_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path("mission_config_used.json").write_text(
        json.dumps(json_safe_config(config), indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 64)
    print("FINAL MISSION REPORT")
    print("=" * 64)
    print(json.dumps({key: value for key, value in report.items() if key != "trace"}, indent=2))
    print("\nSaved: mission_report.json (includes the complete action trace)")
    print("Saved: mission_config_used.json (mission inputs)")
    print("Note: the agent learns hidden clue information only by scanning.")

if __name__ == "__main__":
    main()
