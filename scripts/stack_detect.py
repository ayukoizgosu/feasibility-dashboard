
#!/usr/bin/env python3
"""Heuristic stack detector for polyglot vibe-coding repos."""
from __future__ import annotations
import os, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def exists(*parts: str) -> bool:
    return (ROOT / pathlib.Path(*parts)).exists()

def detect() -> dict:
    hints = []
    if exists("package.json"):
        hints.append("node")
    if any(ROOT.glob("**/*.ts")) or any(ROOT.glob("**/*.tsx")):
        hints.append("typescript")
    if any(ROOT.glob("**/*.py")) or exists("pyproject.toml") or exists("requirements.txt"):
        hints.append("python")
    if any(ROOT.glob("**/*.go")) or exists("go.mod"):
        hints.append("go")
    if any(ROOT.glob("**/*.rs")) or exists("Cargo.toml"):
        hints.append("rust")
    if exists("docker-compose.yml") or exists("Dockerfile"):
        hints.append("docker")
    if exists("openapi.yaml") or exists("openapi.yml"):
        hints.append("openapi")
    return {"root": str(ROOT), "hints": sorted(set(hints))}

if __name__ == "__main__":
    print(json.dumps(detect(), indent=2))
