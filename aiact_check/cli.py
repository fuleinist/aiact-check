"""argparse-based CLI: scan, deadlines, init-docs, version."""

from __future__ import annotations

import argparse
import sys

from aiact_check import DISCLAIMER, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aiact-check",
        description="EU AI Act compliance scanner (heuristic, not legal advice).",
        epilog=DISCLAIMER,
    )
    parser.add_argument("--version", action="version", version=f"aiact-check {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan a project for AI usage and compliance risks.")
    p_scan.add_argument("path", nargs="?", default=".", help="Project directory to scan (default: cwd)")
    p_scan.add_argument("--format", choices=["terminal", "json", "yaml", "markdown"], default="terminal")
    p_scan.add_argument("--output", metavar="FILE", help="Write report to FILE instead of stdout")
    p_scan.add_argument("--config", metavar="FILE", help="Path to aiact-check.toml (default: <path>/aiact-check.toml)")
    p_scan.add_argument("--quiet", action="store_true", help="Suppress terminal summary when writing to file")

    sub.add_parser("deadlines", help="Show EU AI Act compliance timeline relative to today.")

    p_docs = sub.add_parser("init-docs", help="Scaffold starter compliance documentation.")
    p_docs.add_argument("path", nargs="?", default=".", help="Project directory (default: cwd)")
    p_docs.add_argument("--force", action="store_true", help="Overwrite existing files")
    p_docs.add_argument("--report", metavar="FILE", help="JSON report from a previous scan to embed in CHECKLIST.md")

    return parser


def _force_utf8_stdio() -> None:
    """Windows consoles may default to cp1252; make emoji/unicode output safe."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        from aiact_check.cli_commands import run_scan

        return run_scan(args)
    if args.command == "deadlines":
        from aiact_check.cli_commands import run_deadlines

        return run_deadlines(args)
    if args.command == "init-docs":
        from aiact_check.cli_commands import run_init_docs

        return run_init_docs(args)
    parser.error(f"unknown command: {args.command}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
