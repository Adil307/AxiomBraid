from __future__ import annotations

import json
import platform
import tempfile
import time
from pathlib import Path

import pandas as pd
import axiombraid as AB


def make_frame(rows: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Record_ID": [f"R{i:07d}" for i in range(rows)],
            "Category": ["A", "B", " C ", "c"] * (rows // 4)
            + ["A"] * (rows % 4),
            "Value": [float(i % 100) for i in range(rows)],
            "Attendance": [float(i % 101) for i in range(rows)],
        }
    )


def timed(callable_):
    start = time.perf_counter()
    value = callable_()
    return value, time.perf_counter() - start


def main() -> int:
    records = []
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        cache_dir = directory / "cache"
        for rows in (1_000, 10_000, 50_000):
            frame = make_frame(rows)
            _, inspect_seconds = timed(lambda: AB.inspect(frame))
            miss, cache_miss_seconds = timed(
                lambda: AB.cached_inspect(frame, cache_dir=cache_dir, refresh=True)
            )
            hit, cache_hit_seconds = timed(
                lambda: AB.cached_inspect(frame, cache_dir=cache_dir)
            )
            records.append(
                {
                    "rows": rows,
                    "columns": len(frame.columns),
                    "inspect_seconds": inspect_seconds,
                    "cache_miss_seconds": cache_miss_seconds,
                    "cache_hit_seconds": cache_hit_seconds,
                    "cache_hit_confirmed": hit["cache_hit"],
                }
            )

        stream_frame = make_frame(100_000)
        csv_path = directory / "stream.csv"
        stream_frame.to_csv(csv_path, index=False)
        stream_result, stream_seconds = timed(
            lambda: AB.stream_csv(
                csv_path,
                chunksize=20_000,
                sample_rows=10_000,
                random_state=42,
            )
        )

    payload = {
        "benchmark_version": 1,
        "axiombraid": AB.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "full_inspection": records,
        "streaming": {
            "rows": stream_result["streaming"]["exact_rows"],
            "sample_rows": stream_result["streaming"]["sample_rows"],
            "seconds": stream_seconds,
        },
        "warning": (
            "Local benchmark only. Results are not portable across hardware, "
            "operating systems, Python versions, or pandas versions."
        ),
    }
    output = Path(__file__).with_name("baseline_1_0.json")
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
