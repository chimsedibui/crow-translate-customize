#!/usr/bin/env python3
"""Benchmark OpenAI Vision OCR latency and accuracy, using the real OpenAiOcrProvider
(src/py_crow_tool/providers/openai_ocr.py) so results reflect the shipped code path.

Usage:
    export PY_CROW_OPENAI_API_KEY=sk-...
    python scripts/bench_ocr_openai.py --images-dir data/bench_images --runs 3

Same image/ground-truth layout as scripts/bench_ocr_tesseract.py:
    images/<group>/<name>.png  (+ optional <name>.txt ground truth, same stem)
Group names are informational only here (OpenAI needs no per-language model), but are
still used as an optional --language-hint per group via --group-language-hint.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from py_crow_tool.core.ocr_models import OcrException, OcrRequest  # noqa: E402
from py_crow_tool.providers.openai_ocr import OpenAiOcrProvider  # noqa: E402

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass
class ImageCase:
    path: Path
    group: str
    language_hint: str | None
    ground_truth: str | None
    size_bytes: int


@dataclass
class RunResult:
    case: ImageCase
    run_index: int
    latency_ms: float
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    image_bytes_sent: int | None = None
    error: str | None = None


def parse_group_hints(spec: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        group, _, hint = pair.partition("=")
        if hint:
            mapping[group.strip()] = hint.strip()
    return mapping


def discover_cases(images_dir: Path, gt_ext: str, group_hints: dict[str, str]) -> list[ImageCase]:
    cases: list[ImageCase] = []
    for path in sorted(images_dir.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        group = path.parent.name if path.parent != images_dir else "ungrouped"
        gt_path = path.with_suffix(gt_ext)
        ground_truth = gt_path.read_text(encoding="utf-8").strip() if gt_path.exists() else None
        cases.append(
            ImageCase(
                path=path,
                group=group,
                language_hint=group_hints.get(group),
                ground_truth=ground_truth,
                size_bytes=path.stat().st_size,
            )
        )
    return cases


def char_error_rate(hypothesis: str, reference: str) -> float | None:
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


async def run_ocr(provider: OpenAiOcrProvider, case: ImageCase, run_index: int) -> RunResult:
    image_bytes = case.path.read_bytes()
    request = OcrRequest(image=image_bytes, language_hint=case.language_hint)
    start = time.perf_counter()
    try:
        result = await provider.recognize(request)
        latency_ms = (time.perf_counter() - start) * 1000
        usage = result.metadata.get("usage", {}) if result.metadata else {}
        return RunResult(
            case=case,
            run_index=run_index,
            latency_ms=latency_ms,
            text=result.text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            image_bytes_sent=result.metadata.get("image_bytes_sent") if result.metadata else None,
        )
    except OcrException as error:
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(case=case, run_index=run_index, latency_ms=latency_ms, text="", error=f"{error.kind}: {error}")


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
        total_tokens = sum(
            (r.prompt_tokens or 0) + (r.completion_tokens or 0) for r in group_results if r.error is None
        )
        return {
            "runs": len(group_results),
            "errors": sum(1 for r in group_results if r.error is not None),
            "p50_latency_ms": round(percentile(latencies, 50), 1) if latencies else None,
            "p95_latency_ms": round(percentile(latencies, 95), 1) if latencies else None,
            "mean_latency_ms": round(statistics.mean(latencies), 1) if latencies else None,
            "mean_cer": round(statistics.mean(cers), 4) if cers else None,
            "exact_match_rate": round(sum(exact) / len(exact), 3) if exact else None,
            "cases_with_ground_truth": len(cers),
            "total_tokens": total_tokens,
        }

    summary = {"groups": {group: group_stats(rs) for group, rs in sorted(by_group.items())}}
    summary["overall"] = group_stats(results)
    return summary


def write_csv(results: list[RunResult], out_path: Path) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image", "group", "run_index", "size_bytes_original", "size_bytes_sent", "latency_ms", "cer",
            "exact_match", "prompt_tokens", "completion_tokens", "error", "recognized_text",
        ])
        for r in results:
            cer = char_error_rate(r.text, r.case.ground_truth) if r.case.ground_truth is not None else ""
            exact = (
                unicodedata.normalize("NFC", r.text) == unicodedata.normalize("NFC", r.case.ground_truth)
                if r.case.ground_truth is not None
                else ""
            )
            writer.writerow([
                str(r.case.path), r.case.group, r.run_index, r.case.size_bytes, r.image_bytes_sent or "",
                round(r.latency_ms, 1), cer, exact, r.prompt_tokens or "", r.completion_tokens or "",
                r.error or "", r.text.replace("\n", "\\n"),
            ])


def print_summary(summary: dict, env: dict) -> None:
    print("Environment:")
    for key, value in env.items():
        print(f"  {key}: {value}")
    print()
    header = f"{'group':<10} {'runs':>5} {'errs':>5} {'p50 ms':>8} {'p95 ms':>8} {'mean CER':>9} {'exact %':>8} {'tokens':>8}"
    print(header)
    print("-" * len(header))
    for group, stats in summary["groups"].items():
        print(
            f"{group:<10} {stats['runs']:>5} {stats['errors']:>5} "
            f"{stats['p50_latency_ms'] if stats['p50_latency_ms'] is not None else '-':>8} "
            f"{stats['p95_latency_ms'] if stats['p95_latency_ms'] is not None else '-':>8} "
            f"{stats['mean_cer'] if stats['mean_cer'] is not None else '-':>9} "
            f"{(stats['exact_match_rate'] * 100) if stats['exact_match_rate'] is not None else '-':>8} "
            f"{stats['total_tokens']:>8}"
        )
    o = summary["overall"]
    print("-" * len(header))
    print(
        f"{'overall':<10} {o['runs']:>5} {o['errors']:>5} "
        f"{o['p50_latency_ms'] if o['p50_latency_ms'] is not None else '-':>8} "
        f"{o['p95_latency_ms'] if o['p95_latency_ms'] is not None else '-':>8} "
        f"{o['mean_cer'] if o['mean_cer'] is not None else '-':>9} "
        f"{(o['exact_match_rate'] * 100) if o['exact_match_rate'] is not None else '-':>8} "
        f"{o['total_tokens']:>8}"
    )


async def main_async(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("PY_CROW_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not api_key:
        print("error: no API key. Pass --api-key or set PY_CROW_OPENAI_API_KEY / OPENAI_API_KEY", file=sys.stderr)
        return 1

    if not args.images_dir.is_dir():
        print(f"error: {args.images_dir} is not a directory", file=sys.stderr)
        return 1

    group_hints = parse_group_hints(args.group_language_hint)
    cases = discover_cases(args.images_dir, args.gt_ext, group_hints)
    if not cases:
        print(f"error: no images found under {args.images_dir}", file=sys.stderr)
        return 1

    with_gt = sum(1 for c in cases if c.ground_truth is not None)
    print(f"Found {len(cases)} images ({with_gt} with ground truth) across groups: "
          f"{sorted({c.group for c in cases})}")

    provider = OpenAiOcrProvider(
        api_key,
        model=args.model,
        max_dimension=args.max_dimension,
        image_format=args.image_format,
        jpeg_quality=args.jpeg_quality,
        detail=args.detail,
        reasoning_effort=args.reasoning_effort,
    )
    results: list[RunResult] = []
    total = len(cases) * args.runs
    done = 0
    try:
        for case in cases:
            for run_index in range(args.runs):
                result = await run_ocr(provider, case, run_index)
                results.append(result)
                done += 1
                if result.error:
                    print(f"  [{done}/{total}] ERROR {case.path.name}: {result.error}", file=sys.stderr)
                else:
                    print(f"  [{done}/{total}] {case.path.name}: {result.latency_ms:.0f} ms")
    finally:
        await provider.close()

    write_csv(results, args.out_csv)
    print(f"\nWrote per-run details to {args.out_csv}\n")

    summary = summarize(results)
    env = {
        "model": args.model,
        "runs_per_image": args.runs,
        "max_dimension": args.max_dimension,
        "image_format": args.image_format,
        "jpeg_quality": args.jpeg_quality,
        "detail": args.detail,
    }
    print_summary(summary, env)

    if args.summary_json:
        args.summary_json.write_text(json.dumps({"env": env, "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote summary JSON to {args.summary_json}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3, help="Repeat count per image (default: 3) -- costs real tokens each run")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI vision model (default: gpt-4o-mini)")
    parser.add_argument("--api-key", default="", help="Overrides PY_CROW_OPENAI_API_KEY / OPENAI_API_KEY env vars")
    parser.add_argument("--max-dimension", type=int, default=1280, help="Resize cap on longest side before sending (default: 1280)")
    parser.add_argument("--image-format", choices=["jpeg", "png"], default="jpeg", help="Re-encode format sent to the API (default: jpeg)")
    parser.add_argument("--jpeg-quality", type=int, default=87, help="JPEG quality when --image-format=jpeg (default: 87)")
    parser.add_argument("--detail", choices=["low", "high", "auto"], default="high", help="OpenAI image detail level (default: high)")
    parser.add_argument("--reasoning-effort", default="minimal", help="GPT-5-family only: minimal/low/medium/high (default: minimal)")
    parser.add_argument("--gt-ext", default=".txt", help="Ground-truth file extension, same stem as image (default: .txt)")
    parser.add_argument(
        "--group-language-hint", default="", help="Comma-separated group=hint, e.g. 'vi=Vietnamese,en=English'"
    )
    parser.add_argument("--out-csv", type=Path, default=Path("ocr_bench_openai_results.csv"))
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
