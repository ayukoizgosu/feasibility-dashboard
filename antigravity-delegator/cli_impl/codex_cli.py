#!/usr/bin/env python3
from __future__ import annotations
import runpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "codex_cli.py"
sys.path.insert(0, str(ROOT))
runpy.run_path(str(TARGET), run_name="__main__")
