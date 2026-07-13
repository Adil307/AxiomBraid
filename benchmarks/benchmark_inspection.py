"""Simple reproducible local benchmark; not a scientific comparison."""
from time import perf_counter
import pandas as pd
import axiombraid as AB

for rows in (1_000, 10_000, 100_000):
    frame = pd.DataFrame({"ID": [f"S{i}" for i in range(rows)], "Value": range(rows), "Group": ["A","B"]*(rows//2)})
    start = perf_counter(); AB.inspect(frame); elapsed = perf_counter()-start
    print(f"rows={rows:,} seconds={elapsed:.4f}")
