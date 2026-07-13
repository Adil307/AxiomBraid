"""Folder-level batch analysis for AxiomBraid."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import load_config
from .inspector import DataGuide

ProgressCallback = Callable[[int, int, dict[str, Any]], None]


class BatchAnalyzer:
    """Analyze supported datasets with isolated errors and safe parallel workers."""

    SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"}

    def __init__(self, folder, *, config=None, recursive=None):
        self.folder = Path(folder)
        if not self.folder.exists():
            raise FileNotFoundError(f"Batch folder not found: {self.folder}")
        if not self.folder.is_dir():
            raise ValueError(f"Batch path is not a folder: {self.folder}")
        self.config = load_config(config)
        self.recursive = self.config["batch"]["recursive"] if recursive is None else bool(recursive)

    def discover_files(self) -> list[Path]:
        iterator = self.folder.rglob("*") if self.recursive else self.folder.glob("*")
        return sorted(path for path in iterator if path.is_file() and path.suffix.lower() in self.SUPPORTED_SUFFIXES)

    @staticmethod
    def _safe_stem(path: Path) -> str:
        value = "".join(c if c.isalnum() or c in {"-", "_"} else "_" for c in path.stem).strip("_")
        return value or "dataset"

    def _analyze_one(self, index, path, output, selected_formats, selected_language, selected_theme, selected_mode, selected_sample_rows, selected_strategy, selected_random_state):
        safe_stem = f"{index:03d}_{self._safe_stem(path)}"
        try:
            guide = DataGuide.from_config(path, self.config).prepare_analysis(
                mode=selected_mode,
                sample_rows=selected_sample_rows,
                strategy=selected_strategy,
                random_state=selected_random_state,
            )
            result = guide.inspect(language=selected_language)
            outputs = {}
            if "json" in selected_formats:
                outputs["json"] = str(guide.export_json(output/f"{safe_stem}.json", selected_language))
            if "html" in selected_formats:
                outputs["html"] = str(guide.export_html(output/f"{safe_stem}.html", selected_language, theme=selected_theme))
            if "charts" in selected_formats:
                outputs["charts"] = [str(item) for item in guide.export_charts(output/f"{safe_stem}_charts")]
            return index, {
                "file": str(path.resolve()), "status": "success", "shape": result["shape"],
                "quality_score": result["data_quality"]["score"], "quality_rating": result["data_quality"]["rating"],
                "issue_count": len(result["issues"]), "performance": result["performance"], "outputs": outputs,
            }
        except Exception as exc:
            return index, {"file": str(path.resolve()), "status": "error", "error_type": type(exc).__name__, "message": str(exc), "outputs": {}}

    def analyze(self, output_dir="axiombraid_batch_reports", *, formats=None, language=None, html_theme=None, mode=None, sample_rows=None, strategy=None, random_state=None, continue_on_error=None, workers=None, progress_callback: ProgressCallback | None = None):
        output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
        report_config, perf = self.config["report"], self.config["performance"]
        selected_formats = [str(item).strip().lower() for item in (formats if formats is not None else report_config["formats"])]
        invalid = sorted(set(selected_formats)-{"json","html","charts"})
        if invalid: raise ValueError("Unsupported batch format(s): "+", ".join(invalid))
        selected_language = language or report_config["language"]
        selected_theme = html_theme or report_config["html_theme"]
        selected_mode = mode or perf["mode"]
        selected_sample_rows = int(sample_rows or perf["sample_rows"])
        selected_strategy = strategy or perf["strategy"]
        selected_random_state = int(random_state if random_state is not None else perf["random_state"])
        keep_going = self.config["batch"]["continue_on_error"] if continue_on_error is None else bool(continue_on_error)
        selected_workers = int(workers if workers is not None else self.config["batch"].get("workers", 1))
        if selected_workers < 1: raise ValueError("workers must be a positive integer.")
        if selected_workers > 1 and "charts" in selected_formats:
            raise ValueError("Parallel batch chart export is disabled for thread safety; use workers=1.")

        files = self.discover_files(); total = len(files); indexed = list(enumerate(files, start=1)); results = {}
        if selected_workers == 1:
            for index, path in indexed:
                result_index, entry = self._analyze_one(index, path, output, selected_formats, selected_language, selected_theme, selected_mode, selected_sample_rows, selected_strategy, selected_random_state)
                results[result_index] = entry
                if progress_callback: progress_callback(len(results), total, entry)
                if entry["status"] == "error" and not keep_going:
                    if entry.get("error_type") == "ValueError":
                        raise ValueError(entry["message"])
                    if entry.get("error_type") == "FileNotFoundError":
                        raise FileNotFoundError(entry["message"])
                    raise RuntimeError(entry["message"])
        else:
            with ThreadPoolExecutor(max_workers=selected_workers, thread_name_prefix="axiombraid") as pool:
                futures = {pool.submit(self._analyze_one, index, path, output, selected_formats, selected_language, selected_theme, selected_mode, selected_sample_rows, selected_strategy, selected_random_state): index for index, path in indexed}
                for future in as_completed(futures):
                    result_index, entry = future.result(); results[result_index] = entry
                    if progress_callback: progress_callback(len(results), total, entry)
                    if entry["status"] == "error" and not keep_going:
                        for pending in futures: pending.cancel()
                        raise RuntimeError(entry["message"])
        entries = [results[index] for index, _ in indexed]
        success_count = sum(entry["status"] == "success" for entry in entries)
        summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "folder": str(self.folder.resolve()), "recursive": self.recursive, "workers": selected_workers, "file_count": total, "success_count": success_count, "error_count": total-success_count, "formats": selected_formats, "entries": entries}
        summary_json = output/"batch_summary.json"; summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        summary_csv = output/"batch_summary.csv"
        with summary_csv.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["file","status","rows","columns","quality_score","quality_rating","issue_count","sampled","message"]); writer.writeheader()
            for entry in entries:
                shape, performance = entry.get("shape",{}), entry.get("performance",{})
                writer.writerow({"file":entry["file"],"status":entry["status"],"rows":shape.get("rows",""),"columns":shape.get("columns",""),"quality_score":entry.get("quality_score",""),"quality_rating":entry.get("quality_rating",""),"issue_count":entry.get("issue_count",""),"sampled":performance.get("sampled",""),"message":entry.get("message","")})
        summary["summary_json"], summary["summary_csv"] = str(summary_json.resolve()), str(summary_csv.resolve())
        return summary


def batch_analyze(folder, output_dir="axiombraid_batch_reports", **kwargs):
    analyzer_keys = {"config", "recursive"}
    analyzer_kwargs = {key: kwargs.pop(key) for key in list(kwargs) if key in analyzer_keys}
    return BatchAnalyzer(folder, **analyzer_kwargs).analyze(output_dir, **kwargs)
