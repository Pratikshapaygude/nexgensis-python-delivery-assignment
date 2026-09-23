
import json
import math
import random
import csv
import sys


# ---------------------------------------------------------------------------
# 1. DATA LOADING  -  manual JSON parsing (just the standard library `json`
#    module + plain dict/list handling, no external data libraries)
# ---------------------------------------------------------------------------

def _normalise_points(data):
    """Turn either of the two accepted point-map shapes into one plain
    {"id": (x, y)} dict, so the rest of the program only has one format
    to deal with.

        dict shape:  {"W1": [0, 0], "W2": [50, 75]}
        list shape:  [{"id": "W1", "location": [0, 0]}, ...]
    """
    if isinstance(data, dict):
        return {point_id: tuple(coords) for point_id, coords in data.items()}

    normalised = {}
    for item in data:
        normalised[item["id"]] = tuple(item["location"])
    return normalised


def load_data(path):
    """Read and manually parse the input JSON file.

    Returns
    -------
    warehouses : dict   {"W1": (x, y), ...}
    agents     : dict   {"A1": (x, y), ...}
    packages   : list   [{"id": "P1", "warehouse": "W1", "destination": (x, y)}, ...]
    """
    with open(path, "r") as f:
        raw = json.load(f)

    warehouses = _normalise_points(raw["warehouses"])
    agents = _normalise_points(raw["agents"])

    packages = []
    for pkg in raw["packages"]:
        # Some files call the field "warehouse", others "warehouse_id".
        warehouse_id = pkg.get("warehouse", pkg.get("warehouse_id"))
        packages.append({
            "id": pkg["id"],
            "warehouse": warehouse_id,
            "destination": tuple(pkg["destination"]),
        })

    return warehouses, agents, packages


# ---------------------------------------------------------------------------
# 2. DISTANCE CALCULATION
# ---------------------------------------------------------------------------

def euclidean_distance(point_a, point_b):
    """Straight-line distance between two (x, y) points."""
    return math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)


# ---------------------------------------------------------------------------
# 3. AGENT <-> PACKAGE ASSIGNMENT
# ---------------------------------------------------------------------------

def assign_packages_to_agents(agents, warehouses, packages):
    """Assign every package to the agent that is closest (Euclidean
    distance) to that package's warehouse.

    Returns {agent_id: [package, package, ...]} - every agent gets an
    entry, even if it ends up with an empty list.
    """
    assignment = {agent_id: [] for agent_id in agents}

    for pkg in packages:
        warehouse_location = warehouses[pkg["warehouse"]]
        nearest_agent = min(
            agents,
            key=lambda agent_id: euclidean_distance(agents[agent_id], warehouse_location),
        )
        assignment[nearest_agent].append(pkg)

    return assignment


# ---------------------------------------------------------------------------
# 4. SIMULATION
# ---------------------------------------------------------------------------

def simulate_deliveries(agents, warehouses, assignment, simulate_delays=False, seed=None):
    """Walk each agent through its assigned packages, in the order they
    were assigned, tracking the distance travelled.

    For every package the agent travels:
        current position -> warehouse (pickup) -> destination (drop-off)
    and its "current position" becomes the destination for the next
    package, so agents don't teleport back to their start point between
    deliveries.

    Parameters
    ----------
    simulate_delays : bonus feature - if True, each delivery also gets a
        random delay (in minutes) to mimic traffic/weather etc.

    Returns
    -------
    stats  : {agent_id: {"packages_delivered", "total_distance", "efficiency"}}
    routes : {agent_id: [("start", (x, y)), ("pickup P1", (x, y)), ...]}
    delays : {agent_id: total_delay_minutes}
    """
    if seed is not None:
        random.seed(seed)

    stats, routes, delays = {}, {}, {}

    for agent_id, pkgs in assignment.items():
        position = agents[agent_id]
        total_distance = 0.0
        route = [("start", position)]
        agent_delay = 0

        for pkg in pkgs:
            warehouse_location = warehouses[pkg["warehouse"]]
            destination = pkg["destination"]

            total_distance += euclidean_distance(position, warehouse_location)
            route.append((f"pickup {pkg['id']}", warehouse_location))

            total_distance += euclidean_distance(warehouse_location, destination)
            route.append((f"deliver {pkg['id']}", destination))

            position = destination  # agent now stands at the drop-off point

            if simulate_delays:
                # Mostly on time, occasionally a small delay - just for flavour.
                agent_delay += random.choice([0, 0, 0, 5, 10, 15])

        packages_delivered = len(pkgs)
        # Efficiency = packages delivered per 100 units of distance travelled.
        # Higher is better; an idle agent (no distance travelled) scores 0.
        efficiency = (packages_delivered / total_distance * 100) if total_distance > 0 else 0.0

        stats[agent_id] = {
            "packages_delivered": packages_delivered,
            "total_distance": round(total_distance, 2),
            "efficiency": round(efficiency, 2),
        }
        routes[agent_id] = route
        delays[agent_id] = agent_delay

    return stats, routes, delays


# ---------------------------------------------------------------------------
# 5. REPORT
# ---------------------------------------------------------------------------

def build_report(stats):
    """Attach the "best_agent" field (highest efficiency) to the stats."""
    report = dict(stats)
    # Only consider agents that actually delivered something as "best",
    # so an idle agent (efficiency 0) never wins by default.
    active_agents = [a for a in stats if stats[a]["packages_delivered"] > 0]
    candidates = active_agents or list(stats)
    best_agent = max(candidates, key=lambda a: stats[a]["efficiency"])
    report["best_agent"] = best_agent
    return report


def save_report(report, path="report.json"):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# BONUS 1: ASCII route visualisation
# ---------------------------------------------------------------------------

def render_ascii_map(warehouses, agents, packages, width=60, height=25):
    """Draw a very simple ASCII scatter-plot of every warehouse (W),
    agent start position (A) and package destination (.) so you can
    eyeball the overall layout."""
    all_points = list(warehouses.values()) + list(agents.values()) + \
        [p["destination"] for p in packages]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(value, lo, hi, size):
        if hi == lo:
            return size // 2
        return int((value - lo) / (hi - lo) * (size - 1))

    grid = [[" "] * width for _ in range(height)]

    def plot(point, symbol):
        gx = scale(point[0], min_x, max_x, width)
        gy = height - 1 - scale(point[1], min_y, max_y, height)  # flip so y grows upward
        grid[gy][gx] = symbol

    for pkg in packages:
        plot(pkg["destination"], ".")
    for loc in warehouses.values():
        plot(loc, "W")
    for loc in agents.values():
        plot(loc, "A")

    lines = ["".join(row) for row in grid]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# BONUS 2: new agent joining mid-day
# ---------------------------------------------------------------------------

def add_mid_day_agent(agents, warehouses, remaining_packages, new_agent_id, new_agent_location):
    """Simulate a new agent showing up partway through the day. Adds the
    agent to the roster and re-runs the nearest-agent assignment for
    whatever packages hadn't been delivered yet, so the new agent can
    pick up some of the remaining workload."""
    agents = dict(agents)  # don't mutate the caller's dict
    agents[new_agent_id] = new_agent_location
    new_assignment = assign_packages_to_agents(agents, warehouses, remaining_packages)
    return agents, new_assignment


# ---------------------------------------------------------------------------
# BONUS 3: export the top performer to CSV
# ---------------------------------------------------------------------------

def export_top_performer_csv(report, path="top_performer.csv"):
    best_agent = report["best_agent"]
    best_stats = report[best_agent]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        writer.writerow([
            best_agent,
            best_stats["packages_delivered"],
            best_stats["total_distance"],
            best_stats["efficiency"],
        ])


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main(data_path="data.json", report_path="report.json", show_ascii=True, seed=42):
    warehouses, agents, packages = load_data(data_path)

    assignment = assign_packages_to_agents(agents, warehouses, packages)
    stats, routes, delays = simulate_deliveries(
        agents, warehouses, assignment, simulate_delays=True, seed=seed
    )
    report = build_report(stats)

    # Sanity check called out in the assignment notes: every package must
    # end up delivered by exactly one agent.
    total_delivered = sum(v["packages_delivered"] for v in stats.values())
    assert total_delivered == len(packages), (
        f"Mismatch: {total_delivered} delivered vs {len(packages)} packages in input!"
    )

    save_report(report, report_path)
    export_top_performer_csv(report, path=report_path.replace(".json", "_top_performer.csv"))

    print(f"Loaded: {len(warehouses)} warehouses, {len(agents)} agents, {len(packages)} packages")
    print(json.dumps(report, indent=2))
    print("\nSimulated delivery delays (minutes) per agent:", delays)

    if show_ascii:
        print("\nASCII map (W = warehouse, A = agent start, . = package destination)")
        print(render_ascii_map(warehouses, agents, packages))

    return report


if __name__ == "__main__":
    data_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    report_file = sys.argv[2] if len(sys.argv) > 2 else "report.json"
    main(data_file, report_file)
