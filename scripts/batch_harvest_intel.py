"""Batch script to harvest market intelligence for multiple suburbs."""

import os
import subprocess
import sys

suburbs = [
    "Doncaster East",
    "Doncaster",
    "Donvale",
    "Templestowe",
    "Templestowe Lower",
    "Bulleen",
]

print(f"🚀 Starting batch market intelligence harvest for {len(suburbs)} suburbs...")

# Ensure PYTHONPATH is set
env = os.environ.copy()
env["PYTHONPATH"] = "src"

for suburb in suburbs:
    print(f"\n--- Processing {suburb} ---")
    try:
        # Run Domain SOLD scrape
        cmd = [
            sys.executable,
            "-m",
            "scanner.ingest.domain",
            "--suburb",
            suburb,
            "--type",
            "sold",
            "--limit",
            "3",  # 3 pages per suburb = ~60 listings
        ]
        subprocess.run(cmd, env=env, check=True)
        print(f"✅ Finished {suburb}")
    except Exception as e:
        print(f"❌ Failed to process {suburb}: {e}")

print("\n✨ All suburbs processed!")
