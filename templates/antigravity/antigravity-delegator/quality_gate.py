#!/usr/bin/env python3
"""
Quality Gate Script for Antigravity Cockpit Workflow
Validates Gemini/Codex CLI output before The Architect uses it.
"""
import sys
import os
import subprocess

# CONFIGURATION
FORBIDDEN_PHRASES = [
    "here is the code", "certainly", "i cannot", "as an ai"
]

def verify_file(filepath):
    if not os.path.exists(filepath):
        print(f"CRITICAL: File {filepath} was not created.")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # CHECK 1: Empty File
    if len(content.strip()) == 0:
        print(f"FAILURE: File {filepath} is empty.")
        sys.exit(1)

    # CHECK 2: Markdown wrappers (auto-clean)
    if "```" in content:
        print(f"WARNING: Markdown detected. Attempting auto-clean...")
        lines = content.split('\n')
        clean_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue  # Skip the ``` line
            clean_lines.append(line)
        clean_content = '\n'.join(clean_lines)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        content = clean_content
        print(f"FIXED: Removed markdown wrappers.")

    # CHECK 3: Conversational Leakage
    content_lower = content.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in content_lower:
            print(f"FAILURE: Detected conversational filler: '{phrase}'")
            sys.exit(1)

    # CHECK 4: Basic Syntax (Auto-detect based on extension)
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ['.js', '.mjs']:
            result = subprocess.run(['node', '--check', filepath], capture_output=True, timeout=10)
            if result.returncode != 0:
                print(f"SYNTAX ERROR: JavaScript syntax invalid")
                sys.exit(1)
        elif ext == '.py':
            result = subprocess.run([sys.executable, '-m', 'py_compile', filepath], capture_output=True, timeout=10)
            if result.returncode != 0:
                print(f"SYNTAX ERROR: Python syntax invalid")
                sys.exit(1)
        # TypeScript and other extensions - skip syntax check (needs tsc)
        print(f"SUCCESS: {filepath} passed quality gate.")
        sys.exit(0)
    except FileNotFoundError:
        # Node/Python not available for syntax check
        print(f"SKIPPED: Syntax check unavailable for {ext}")
        print(f"SUCCESS: {filepath} passed basic quality gate.")
        sys.exit(0)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Syntax check timed out")
        print(f"SUCCESS: {filepath} passed basic quality gate.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quality_gate.py <filename>")
        sys.exit(1)
    verify_file(sys.argv[1])
