"""Command implementations wired to the CLI."""

from __future__ import annotations

import argparse
import sys

from aiact_check import DISCLAIMER


def run_scan(args: argparse.Namespace) -> int:  # pragma: no cover - implemented in cycle 5
    print("scan: not yet implemented", file=sys.stderr)
    return 3


def run_deadlines(args: argparse.Namespace) -> int:  # pragma: no cover - implemented in cycle 3
    print("deadlines: not yet implemented", file=sys.stderr)
    return 3


def run_init_docs(args: argparse.Namespace) -> int:  # pragma: no cover - implemented in cycle 5
    print("init-docs: not yet implemented", file=sys.stderr)
    return 3
