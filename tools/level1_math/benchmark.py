"""Write the fixed held-out benchmark; never use these items for training."""
import json
import random
from pathlib import Path
from ultron_level1 import generate_problem

SEED = 9012026
COUNT = 500
OUT = Path("benchmarks/level1_heldout_500.jsonl")

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    levels = ("easy", "medium", "hard")
    records = [generate_problem(rng, levels[i % 3]) for i in range(COUNT)]
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for i, record in enumerate(records):
            f.write(json.dumps({"id": f"L1-HOLDOUT-{i+1:04d}", **record}, sort_keys=True) + "\n")
    print(f"Wrote {len(records)} held-out problems to {OUT}")

if __name__ == "__main__":
    main()
