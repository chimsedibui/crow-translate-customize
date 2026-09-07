#!/usr/bin/env python3
"""Benchmark Tesseract OCR latency and accuracy on CPU.

Usage:
    python scripts/bench_ocr_tesseract.py --images-dir path/to/images --runs 5

Image layout expected (matches the OCR research doc's pilot set):
    images/
      vi/    001.png  001.txt   (001.txt = ground-truth text, optional)
      en/    001.png  001.txt
      mixed/ 001.png  001.txt

The group name is taken from the immediate parent directory of each image
(falls back to "ungrouped" for a flat directory). Each group is mapped to a
Tesseract language code via --lang-map (default: vi=vie, en=eng, mixed=vie+eng);
any group not listed uses --lang.

Outputs:
  - a per-run CSV (one row per image per run) with latency and CER
  - a per-group summary (p50/p95 latency, mean CER, exact-match rate) printed
    to stdout and written as JSON if --summary-json is given
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
import pytesseract

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

DEFAULT_LANG_MAP = {"vi": "vie", "en": "eng", "mixed": "vie+eng"}


@dataclass
class ImageCase:
    path: Path
    group: str
    lang: str
    ground_truth: str | None
    width: int
    height: int


@dataclass
class RunResult:
    case: ImageCase
    run_index: int
    latency_ms: float
    text: str
    error: str | None = None


def parse_lang_map(spec: str) -> dict[str, str]:
    mapping = dict(DEFAULT_LANG_MAP)
    if not spec:
        return mapping
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        group, _, lang = pair.partition("=")
        if not lang:
            raise ValueError(f"Invalid --lang-map entry (expected group=lang): {pair!r}")
        mapping[group.strip()] = lang.strip()
    return mapping


def discover_cases(images_dir: Path, default_lang: str, lang_map: dict[str, str], gt_ext: str) -> list[ImageCase]:
    cases: list[ImageCase] = []
    for path in sorted(images_dir.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        group = path.parent.name if path.parent != images_dir else "ungrouped"
        lang = lang_map.get(group, default_lang)
        gt_path = path.with_suffix(gt_ext)
        ground_truth = gt_path.read_text(encoding="utf-8").strip() if gt_path.exists() else None
        with Image.open(path) as img:
            width, height = img.size
        cases.append(ImageCase(path=path, group=group, lang=lang, ground_truth=ground_truth, width=width, height=height))
    return cases


def char_error_rate(hypothesis: str, reference: str) -> float | None:
    """Levenshtein-distance CER after Unicode NFC normalization. None if reference is empty."""
    ref = unicodedata.normalize("NFC", reference)
    hyp = unicodedata.normalize("NFC", hypothesis)
    if not ref:
        return None
    if not hyp:
        return 1.0

    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, start=1):
        curr = [i] + [0] * len(hyp)
        for j, hc in enumerate(hyp, start=1):
            cost = 0 if rc == hc else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[len(hyp)] / len(ref)


def run_ocr(case: ImageCase, run_index: int, psm: int, oem: int) -> RunResult:
    config = f"--psm {psm} --oem {oem}"
    start = time.perf_counter()
    try:
        with Image.open(case.path) as img:
            text = pytesseract.image_to_string(img, lang=case.lang, config=config).strip()
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(case=case, run_index=run_index, latency_ms=latency_ms, text=text)
    except Exception as error:  # noqa: BLE001 - report and keep benchmarking other images
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(case=case, run_index=run_index, latency_ms=latency_ms, text="", error=str(error))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def summarize(results: list[RunResult]) -> dict:
    by_group: dict[str, list[RunResult]] = {}
    for r in results:
        by_group.setdefault(r.case.group, []).append(r)

    summary = {"groups": {}, "overall": {}}
    all_latencies = [r.latency_ms for r in results if r.error is None]
    all_cers = [
        char_error_rate(r.text, r.case.ground_truth)
        for r in results
        if r.error is None and r.case.ground_truth is not None
    ]
    all_cers = [c for c in all_cers if c is not None]
    all_exact = [
        unicodedata.normalize("NFC", r.text) == unicodedata.normalize("NFC", r.case.ground_truth)
        for r in results
        if r.error is None and r.case.ground_truth is not None
    ]

    def group_stats(group_results: list[RunResult]) -> dict:
        latencies = [r.latency_ms for r in group_results if r.error is None]
        cers = [
            char_error_rate(r.text, r.case.ground_truth)
            for r in group_results
            if r.error is None and r.case.ground_truth is not None
        ]
        cers = [c for c in cers if c is not None]
        exact = [
            unicodedata.normalize("NFC", r.text) == unicodedata.normalize("NFC", r.case.ground_truth)
            for r in group_results
            if r.error is None and r.case.ground_truth is not None
        ]
        errors = sum(1 for r in group_results if r.error is not None)
        return {
            "runs": len(group_results),
            "errors": errors,
            "p50_latency_ms": round(percentile(latencies, 50), 1) if latencies else None,
            "p95_latency_ms": round(percentile(latencies, 95), 1) if latencies else None,
            "mean_latency_ms": round(statistics.mean(latencies), 1) if latencies else None,
            "mean_cer": round(statistics.mean(cers), 4) if cers else None,
            "worst_cer": round(max(cers), 4) if cers else None,
            "exact_match_rate": round(sum(exact) / len(exact), 3) if exact else None,
            "cases_with_ground_truth": len(cers),
        }

    for group, group_results in sorted(by_group.items()):
        summary["groups"][group] = group_stats(group_results)

    summary["overall"] = {
        "runs": len(results),
        "errors": sum(1 for r in results if r.error is not None),
        "p50_latency_ms": round(percentile(all_latencies, 50), 1) if all_latencies else None,
        "p95_latency_ms": round(percentile(all_latencies, 95), 1) if all_latencies else None,
        "mean_latency_ms": round(statistics.mean(all_latencies), 1) if all_latencies else None,
        "mean_cer": round(statistics.mean(all_cers), 4) if all_cers else None,
        "exact_match_rate": round(sum(all_exact) / len(all_exact), 3) if all_exact else None,
    }
    return summary


def write_csv(results: list[RunResult], out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image", "group", "lang", "run_index", "width", "height", "megapixels",
            "latency_ms", "cer", "exact_match", "error", "recognized_text",
        ])
        for r in results:
            cer = char_error_rate(r.text, r.case.ground_truth) if r.case.ground_truth is not None else ""
            exact = (
                unicodedata.normalize("NFC", r.text) == unicodedata.normalize("NFC", r.case.ground_truth)
                if r.case.ground_truth is not None
                else ""
            )
            writer.writerow([
                str(r.case.path), r.case.group, r.case.lang, r.run_index,
                r.case.width, r.case.height, round(r.case.width * r.case.height / 1_000_000, 3),
                round(r.latency_ms, 1), cer, exact, r.error or "", r.text.replace("\n", "\\n"),
            ])


def print_summary(summary: dict, env: dict) -> None:
    print("Environment:")
    for key, value in env.items():
        print(f"  {key}: {value}")
    print()
    header = f"{'group':<10} {'runs':>5} {'errs':>5} {'p50 ms':>8} {'p95 ms':>8} {'mean CER':>9} {'exact %':>8}"
    print(header)
    print("-" * len(header))
    for group, stats in summary["groups"].items():
        print(
            f"{group:<10} {stats['runs']:>5} {stats['errors']:>5} "
            f"{stats['p50_latency_ms'] if stats['p50_latency_ms'] is not None else '-':>8} "
            f"{stats['p95_latency_ms'] if stats['p95_latency_ms'] is not None else '-':>8} "
            f"{stats['mean_cer'] if stats['mean_cer'] is not None else '-':>9} "
            f"{(stats['exact_match_rate'] * 100) if stats['exact_match_rate'] is not None else '-':>8}"
        )
    o = summary["overall"]
    print("-" * len(header))
    print(
        f"{'overall':<10} {o['runs']:>5} {o['errors']:>5} "
        f"{o['p50_latency_ms'] if o['p50_latency_ms'] is not None else '-':>8} "
        f"{o['p95_latency_ms'] if o['p95_latency_ms'] is not None else '-':>8} "
        f"{o['mean_cer'] if o['mean_cer'] is not None else '-':>9} "
        f"{(o['exact_match_rate'] * 100) if o['exact_match_rate'] is not None else '-':>8}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images-dir", type=Path, required=True, help="Directory of images (searched recursively)")
    parser.add_argument("--runs", type=int, default=3, help="Repeat count per image (default: 3)")
    parser.add_argument("--warmup", type=int, default=1, help="Untimed warmup runs per image, discarded (default: 1)")
    parser.add_argument("--lang", default="vie+eng", help="Default Tesseract lang code for ungrouped/unmapped images")
    parser.add_argument(
        "--lang-map", default="", help="Comma-separated group=lang overrides, e.g. 'vi=vie,en=eng,mixed=vie+eng'"
    )
    parser.add_argument("--gt-ext", default=".txt", help="Ground-truth file extension, same stem as image (default: .txt)")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract --psm value (default: 3)")
    parser.add_argument("--oem", type=int, default=3, help="Tesseract --oem value (default: 3)")
    parser.add_argument("--tesseract-cmd", default="", help="Path to tesseract binary, if not on PATH")
    parser.add_argument("--out-csv", type=Path, default=Path("ocr_bench_results.csv"), help="Per-run CSV output path")
    parser.add_argument("--summary-json", type=Path, default=None, help="Optional path to write the summary as JSON")
    args = parser.parse_args()

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd

    if not args.images_dir.is_dir():
        print(f"error: {args.images_dir} is not a directory", file=sys.stderr)
        return 1

    lang_map = parse_lang_map(args.lang_map)
    cases = discover_cases(args.images_dir, args.lang, lang_map, args.gt_ext)
    if not cases:
        print(f"error: no images found under {args.images_dir}", file=sys.stderr)
        return 1

    with_gt = sum(1 for c in cases if c.ground_truth is not None)
    print(f"Found {len(cases)} images ({with_gt} with ground truth) across groups: "
          f"{sorted({c.group for c in cases})}")

    try:
        tesseract_version = str(pytesseract.get_tesseract_version())
    except Exception as error:  # noqa: BLE001
        print(f"error: could not run tesseract ({error})", file=sys.stderr)
        return 1

    env = {
        "tesseract_version": tesseract_version,
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": str(__import__("os").cpu_count()),
        "python_version": platform.python_version(),
        "psm": args.psm,
        "oem": args.oem,
        "runs_per_image": args.runs,
    }

    for case in cases:
        for _ in range(args.warmup):
            run_ocr(case, run_index=-1, psm=args.psm, oem=args.oem)

    results: list[RunResult] = []
    total = len(cases) * args.runs
    done = 0
    for case in cases:
        for run_index in range(args.runs):
            result = run_ocr(case, run_index=run_index, psm=args.psm, oem=args.oem)
            results.append(result)
            done += 1
            if result.error:
                print(f"  [{done}/{total}] ERROR {case.path.name}: {result.error}", file=sys.stderr)

    write_csv(results, args.out_csv)
    print(f"\nWrote per-run details to {args.out_csv}\n")

    summary = summarize(results)
    print_summary(summary, env)

    if args.summary_json:
        args.summary_json.write_text(json.dumps({"env": env, "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote summary JSON to {args.summary_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
