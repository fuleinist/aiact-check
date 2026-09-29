"""Command implementations wired to the CLI."""

from __future__ import annotations

import argparse
import json
import sys

from aiact_check import DISCLAIMER
from aiact_check.classifier import classify
from aiact_check.config import load_config
from aiact_check.docs import init_docs
from aiact_check.obligations import build_obligations, deadline_awareness
from aiact_check.report import RENDERERS, build_report
from aiact_check.scanner import scan_project


def _emit(text: str, output: str | None, quiet: bool) -> None:
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        if not quiet:
            print(f"Report written to {output}")
    else:
        print(text)


def run_scan(args: argparse.Namespace) -> int:
    cfg = load_config(args.config, args.path)
    scan = scan_project(args.path, exclude=cfg.exclude)
    cls = classify(scan, cfg)
    obligations = build_obligations(cls, cfg)
    deadlines = deadline_awareness()
    report = build_report(scan, cls, cfg, obligations, deadlines)

    try:
        renderer = RENDERERS[args.format]
        text = renderer(report)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    try:
        _emit(text, args.output, args.quiet)
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return 3

    for err in cfg.errors:
        print(f"config warning: {err}", file=sys.stderr)
    for err in scan.errors:
        print(f"scan warning: {err}", file=sys.stderr)
    return int(report["exitCode"])


def run_deadlines(args: argparse.Namespace) -> int:
    awareness = deadline_awareness()
    print("EU AI Act compliance timeline")
    print("=" * 64)
    for entry in awareness.passed:
        print(f"  PASSED   {entry['date']}  {entry['title']}")
        print(f"           {entry['detail']} ({entry['daysSince']} days ago)")
    for entry in awareness.upcoming:
        state = "DUE TODAY" if entry["state"] == "due-today" else f"{entry['daysRemaining']} days remaining"
        print(f"  UPCOMING {entry['date']}  {entry['title']}")
        print(f"           {entry['detail']} ({state})")
    print("=" * 64)
    print(f"  ⚠️  {DISCLAIMER}")
    return 0


def run_init_docs(args: argparse.Namespace) -> int:
    report = None
    if args.report:
        try:
            with open(args.report, encoding="utf-8") as fh:
                report = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read report '{args.report}': {exc}", file=sys.stderr)
            return 3

    created, skipped, errors = init_docs(args.path, force=args.force, report=report)
    for path in created:
        print(f"created: {path}")
    for path in skipped:
        print(f"exists (use --force to overwrite): {path}")
    for err in errors:
        print(f"error: {err}", file=sys.stderr)
    if errors:
        return 3
    if not created and skipped:
        print("nothing to do — all docs already exist")
        return 1
    return 0
