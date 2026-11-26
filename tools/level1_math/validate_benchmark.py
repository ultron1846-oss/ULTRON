import json
from pathlib import Path
from ultron_level1 import verify

path = Path("benchmarks/level1_heldout_500.jsonl")
lines = path.read_text(encoding="utf-8").splitlines()
assert len(lines) == 500, f"expected 500 records, found {len(lines)}"
records = [json.loads(line) for line in lines]
assert len({r["id"] for r in records}) == 500
assert all(verify(r, r["answer"]) for r in records)
print("PASS: 500 unique held-out records; all reference answers verified")
