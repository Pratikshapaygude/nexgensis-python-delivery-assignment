# FastBox Mystery Delivery System

A simulator for FastBox's daily delivery operations: it assigns packages to
the nearest agent, simulates each agent's route, and reports delivery stats
per agent.

## Files

| File                     | Purpose                                                |
|--------------------------|---------------------------------------------------------|
| `delivery_system.py`     | Main script — parsing, assignment, simulation, report  |
| `data.json`              | Sample input (copy of `base_case.json`)                 |
| `report.json`            | Report generated from `data.json`                       |
| `reports/`               | Reports + top-performer CSVs for every sample test case |
| `requirements.txt`       | Dependencies (none — standard library only)              |

## Usage

```bash
python delivery_system.py <input.json> [report_output.json]
```

If no arguments are given, it reads `data.json` and writes `report.json` in
the current directory.

Example:

```bash
python delivery_system.py data.json report.json
```

This also writes `<report_output>_top_performer.csv` alongside the report.

## How it works

1. **Load & normalise input** — `load_data()` reads the JSON with the
   standard `json` module and normalises it, since the sample files use two
   slightly different shapes for `warehouses`/`agents` (a dict of
   `{id: [x, y]}`, or a list of `{"id": ..., "location": [x, y]}`) and two
   different key names for a package's warehouse (`warehouse` vs
   `warehouse_id`).
2. **Assign packages to agents** — `assign_packages_to_agents()` picks,
   for every package, the agent whose *starting position* is closest
   (Euclidean distance) to that package's warehouse.
3. **Simulate the day** — `simulate_deliveries()` walks each agent through
   its assigned packages in order: current position → warehouse (pickup) →
   destination (drop-off), accumulating total distance travelled and
   updating the agent's position after each delivery.
4. **Report** — `build_report()` computes, per agent:
   - `packages_delivered`
   - `total_distance` (rounded to 2 dp)
   - `efficiency` = packages delivered per 100 units of distance travelled
     (higher is better; an idle agent scores 0)
   and adds `best_agent`, the agent with the highest efficiency among
   agents that delivered at least one package.
5. A sanity check asserts that `packages_delivered` summed across agents
   equals the total number of input packages, per the assignment notes.

## Bonus features

- **Random delivery delays** — each delivery gets a small random delay
  (0–15 minutes) to mimic traffic/weather; printed at the end of a run.
- **ASCII route map** — `render_ascii_map()` plots warehouses (`W`), agent
  start positions (`A`) and package destinations (`.`) on a text grid.
- **New agent joining mid-day** — `add_mid_day_agent()` adds a new agent to
  the roster and re-runs the nearest-agent assignment over any packages
  not yet delivered.
- **CSV export of the top performer** — `export_top_performer_csv()` writes
  the best agent's stats to a `.csv` file.

## Testing

The `reports/` folder contains the generated `report.json` and
`*_top_performer.csv` for `base_case.json` and all 10 provided
`test_case_*.json` files. Every run passes the "all packages delivered"
sanity check.
