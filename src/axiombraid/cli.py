"""Command-line interface for AxiomBraid."""

from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Sequence
from ._version import __version__
from .batch import BatchAnalyzer
from .cache import InspectionCache, cached_inspect
from .config import export_config, load_config
from .inspector import DataGuide
from .streaming import stream_csv
from .themes import available_themes
from .evaluation import benchmark_inspection, benchmark_scaling, run_evaluation

def _add_performance_arguments(parser):
    parser.add_argument("--mode", choices=["full","sample","auto"]); parser.add_argument("--sample-rows", type=int)
    parser.add_argument("--strategy", choices=["random","head","systematic"]); parser.add_argument("--random-state", type=int)

def build_parser(prog="axiombraid"):
    parser = argparse.ArgumentParser(prog=prog, description="Explainable, safety-first data quality analysis.")
    parser.add_argument("--version", action="version", version=f"AxiomBraid {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("inspect", help="Inspect one dataset."); p.add_argument("data"); p.add_argument("--config"); p.add_argument("--output", default="axiombraid_report")
    p.add_argument("--format", dest="formats", action="append", choices=["console","json","html","charts"]); p.add_argument("--language", choices=["en","roman_urdu"]); p.add_argument("--theme", choices=available_themes()); p.add_argument("--confidence", action="store_true", help="Include explainable confidence in console, JSON, and HTML reports."); p.add_argument("--confidence-details", choices=["summary","full"], default="full", help="Console confidence detail level."); p.add_argument("--quality-profile", action="store_true", help="Include the explainable Version 2 multi-dimensional quality profile."); p.add_argument("--quality-details", choices=["summary","full"], default="full", help="Console quality-profile detail level."); _add_performance_arguments(p)
    p = subs.add_parser("stream", help="Memory-bounded CSV profiling."); p.add_argument("data"); p.add_argument("--config"); p.add_argument("--chunksize", type=int, default=100000); p.add_argument("--sample-rows", type=int, default=50000); p.add_argument("--random-state", type=int, default=42); p.add_argument("--language", choices=["en","roman_urdu"], default="en"); p.add_argument("--output")
    p = subs.add_parser("cache-inspect", help="Inspect with fingerprint-based caching."); p.add_argument("data"); p.add_argument("--config"); p.add_argument("--cache-dir", default=".axiombraid_cache"); p.add_argument("--language", choices=["en","roman_urdu"], default="en"); p.add_argument("--refresh", action="store_true"); p.add_argument("--output")
    p = subs.add_parser("cache-clear", help="Clear inspection cache."); p.add_argument("--cache-dir", default=".axiombraid_cache")
    p = subs.add_parser("batch", help="Analyze a folder."); p.add_argument("folder"); p.add_argument("--config"); p.add_argument("--output", default="axiombraid_batch_reports"); p.add_argument("--recursive", action="store_true"); p.add_argument("--workers", type=int); p.add_argument("--quiet", action="store_true"); p.add_argument("--format", dest="formats", action="append", choices=["json","html","charts"]); p.add_argument("--language", choices=["en","roman_urdu"]); p.add_argument("--theme", choices=available_themes()); p.add_argument("--stop-on-error", action="store_true"); _add_performance_arguments(p)
    p = subs.add_parser("init-config"); p.add_argument("path")
    p = subs.add_parser("validate"); p.add_argument("data"); p.add_argument("contract"); p.add_argument("--config"); p.add_argument("--output")
    p = subs.add_parser("fingerprint"); p.add_argument("data"); p.add_argument("--config"); p.add_argument("--output")
    p = subs.add_parser("evaluate", help="Inject controlled issues and evaluate detection."); p.add_argument("data"); p.add_argument("--output", default="axiombraid_evaluation"); p.add_argument("--missing-rate", type=float, default=0.05); p.add_argument("--duplicate-rate", type=float, default=0.05); p.add_argument("--text-case-rate", type=float, default=0.05); p.add_argument("--whitespace-rate", type=float, default=0.05); p.add_argument("--invalid-range-rate", type=float, default=0.05); p.add_argument("--outlier-rate", type=float, default=0.05); p.add_argument("--date-format-rate", type=float, default=0.0); p.add_argument("--constant-columns", type=int, default=1); p.add_argument("--identifier-columns", type=int, default=1); p.add_argument("--random-state", type=int, default=42)
    p = subs.add_parser("benchmark", help="Benchmark inspection runtime and Python-tracked memory."); p.add_argument("data"); p.add_argument("--repeats", type=int, default=3); p.add_argument("--sizes", help="Comma-separated scaling sizes, for example 100,1000,5000"); p.add_argument("--output"); p.add_argument("--no-confidence", action="store_true"); p.add_argument("--no-quality-profile", action="store_true")
    subs.add_parser("themes")
    return parser

def _resolved(config,args):
    performance, report = config["performance"], config["report"]
    return {"mode":args.mode or performance["mode"],"sample_rows":args.sample_rows or performance["sample_rows"],"strategy":args.strategy or performance["strategy"],"random_state":args.random_state if args.random_state is not None else performance["random_state"],"language":args.language or report["language"],"theme":args.theme or report["html_theme"]}

def main(argv: Sequence[str] | None=None, *, prog="axiombraid") -> int:
    args=build_parser(prog).parse_args(argv)
    if args.command=="themes":
        print("\n".join(available_themes())); return 0
    if args.command=="init-config": print(f"Configuration created: {export_config(args.path)}"); return 0
    if args.command=="cache-clear": print(f"Cache entries removed: {InspectionCache(args.cache_dir).clear()}"); return 0
    if args.command=="evaluate":
        result=run_evaluation(args.data,corruption_config={"missing_rate":args.missing_rate,"duplicate_rate":args.duplicate_rate,"text_case_rate":args.text_case_rate,"whitespace_rate":args.whitespace_rate,"invalid_range_rate":args.invalid_range_rate,"outlier_rate":args.outlier_rate,"date_format_rate":args.date_format_rate,"constant_columns":args.constant_columns,"identifier_columns":args.identifier_columns,"random_state":args.random_state})
        output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
        corrupted_path=output.with_name(output.name+"_corrupted.csv")
        result["corrupted_dataframe"].to_csv(corrupted_path,index=False)
        serializable={key:value for key,value in result.items() if key!="corrupted_dataframe"}
        report_path=output.with_suffix(".json"); report_path.write_text(json.dumps(serializable,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        metrics=result["detection_evaluation"]["overall"]
        print(f"Evaluation F1: {metrics['f1']:.4f} | Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f}")
        print(f"Evaluation report: {report_path.resolve()}"); print(f"Corrupted dataset: {corrupted_path.resolve()}"); return 0
    if args.command=="benchmark":
        if args.sizes:
            sizes=[int(value.strip()) for value in args.sizes.split(",") if value.strip()]
            result=benchmark_scaling(args.data,sizes=sizes,repeats=args.repeats,include_confidence=not args.no_confidence,include_quality_profile=not args.no_quality_profile)
        else:
            result=benchmark_inspection(args.data,repeats=args.repeats,include_confidence=not args.no_confidence,include_quality_profile=not args.no_quality_profile)
        text=json.dumps(result,indent=2,ensure_ascii=False,default=str)
        if args.output: Path(args.output).write_text(text,encoding="utf-8"); print(f"Benchmark report: {Path(args.output).resolve()}")
        else: print(text)
        return 0
    config=load_config(getattr(args,"config",None))
    if args.command=="stream":
        result=stream_csv(args.data,chunksize=args.chunksize,sample_rows=args.sample_rows,random_state=args.random_state,config=config,language=args.language)
        text=json.dumps(result,indent=2,ensure_ascii=False,default=str)
        if args.output: Path(args.output).write_text(text,encoding="utf-8"); print(f"Streaming report: {Path(args.output).resolve()}")
        else: print(text)
        return 0
    if args.command=="cache-inspect":
        payload=cached_inspect(args.data,cache_dir=args.cache_dir,language=args.language,config=config,refresh=args.refresh)
        text=json.dumps(payload,indent=2,ensure_ascii=False,default=str)
        if args.output: Path(args.output).write_text(text,encoding="utf-8"); print(f"Cached report: {Path(args.output).resolve()}")
        else: print(text)
        return 0
    if args.command=="inspect":
        s=_resolved(config,args); guide=DataGuide.from_config(args.data,config).prepare_analysis(mode=s["mode"],sample_rows=s["sample_rows"],strategy=s["strategy"],random_state=s["random_state"]); formats=args.formats or ["console"]; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
        if "console" in formats: guide.report(s["language"], include_confidence=args.confidence, confidence_details=args.confidence_details, include_quality_profile=args.quality_profile, quality_details=args.quality_details)
        if "json" in formats: print(f"JSON report: {guide.export_json(output.with_suffix('.json'),s['language'],include_confidence=args.confidence,include_quality_profile=args.quality_profile)}")
        if "html" in formats: print(f"HTML report: {guide.export_html(output.with_suffix('.html'),s['language'],theme=s['theme'],include_confidence=args.confidence,include_quality_profile=args.quality_profile)}")
        if "charts" in formats: print(f"Charts created: {len(guide.export_charts(output.parent/f'{output.name}_charts'))}")
        return 0
    if args.command=="batch":
        s=_resolved(config,args)
        def progress(done,total,entry):
            if not args.quiet: print(f"[{done}/{total}] {entry['status'].upper()}: {entry['file']}")
        summary=BatchAnalyzer(args.folder,config=config,recursive=args.recursive or config["batch"]["recursive"]).analyze(args.output,formats=args.formats,language=s["language"],html_theme=s["theme"],mode=s["mode"],sample_rows=s["sample_rows"],strategy=s["strategy"],random_state=s["random_state"],continue_on_error=not args.stop_on_error,workers=args.workers,progress_callback=progress)
        print(f"Batch complete: {summary['success_count']} succeeded, {summary['error_count']} failed."); print(f"Summary: {summary['summary_json']}"); return 0 if summary["error_count"]==0 else 2
    guide=DataGuide.from_config(args.data,config)
    if args.command=="validate":
        result=guide.validate_contract(guide.load_validation_contract(args.contract)); text=json.dumps(result,indent=2,ensure_ascii=False,default=str)
        if args.output: Path(args.output).write_text(text,encoding="utf-8"); print(f"Validation report: {Path(args.output).resolve()}")
        else: print(text)
        return 0 if result["valid"] else 3
    if args.command=="fingerprint":
        result=guide.dataset_fingerprint(); text=json.dumps(result,indent=2,ensure_ascii=False)
        if args.output: print(f"Fingerprint report: {guide.export_fingerprint(args.output)}")
        else: print(text)
        return 0
    return 1

if __name__ == "__main__": raise SystemExit(main())
