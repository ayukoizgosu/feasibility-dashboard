import datetime
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console

# Rich console for terminal output
console = Console()

# ExpressVPN CLI Path
VPN_CLI = r"C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe"

# Australian Location IDs
AU_LOCATIONS = {
    "93": "Adelaide",
    "208": "Brisbane",
    "156": "Melbourne",
    "209": "Perth",
    "81": "Sydney",
    "162": "Sydney - 2",
    "219": "Woolloomooloo",
}

LOG_FILE = "harvest.log"


def log(text, style=None):
    if style:
        console.print(text, style=style)
    else:
        console.print(text)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except Exception as e:
        console.print(f"[red]Logging failed:[/red] {e}")


def run_vpn_command(args, check=True):
    cmd = [VPN_CLI] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check, cwd=os.getcwd()
        )
        if result.stdout.strip():
            log(f"VPN: {result.stdout.strip()}", style="dim")
        return result
    except Exception as e:
        log(f"VPN Command Failed: {e}", style="red")
        return None


def main():
    suburbs = [
        "Doncaster East",
        "Doncaster",
        "Donvale",
        "Templestowe",
        "Templestowe Lower",
        "Bulleen",
    ]

    # Shuffle suburbs to be less predictable
    random.shuffle(suburbs)

    log("🛡️  Secure Market Intelligence Harvester", style="bold blue")
    log(f"Targeting {len(suburbs)} suburbs with rotated sources and VPN.")

    # Reset VPN first
    log("Resetting VPN...", style="dim")
    run_vpn_command(["disconnect"], check=False)
    time.sleep(2)

    for i, suburb in enumerate(suburbs):
        # 1. Rotate VPN every suburb to be safe
        loc_id = random.choice(list(AU_LOCATIONS.keys()))
        log(f"\n[bold green]--- {suburb} ({i+1}/{len(suburbs)}) ---[/bold green]")

        # Disconnect first to ensure a fresh session
        run_vpn_command(["disconnect"], check=False)
        time.sleep(2)

        log(f"Connecting VPN: {AU_LOCATIONS[loc_id]}")
        run_vpn_command(["connect", loc_id])
        time.sleep(12)  # Wait for connection stabilization

        # 2. Pick Source - Domain is currently more reliable for SOLD data
        # We'll do 3 Domain for every 1 REA attempt, or just stick to Domain if REA blocks
        source = "domain" if random.random() < 0.8 else "rea"
        log(f"Selected Source: {source.upper()}", style="cyan")

        # 3. Build Command
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            f"scanner.ingest.{source}",
            "--suburb",
            suburb,
            "--type",
            "sold",
            "--limit",
            "3" if source == "domain" else "1",
        ]

        log(f"Running: {' '.join(cmd)}", style="dim")

        try:
            # Run and stream output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                cwd=os.getcwd(),
            )

            # Read output in real-time
            if process.stdout:
                for line in process.stdout:
                    clean_line = line.rstrip()
                    if clean_line:
                        # Skip noise like 'ValueError' cleanup logs if possible,
                        # but show the core progress
                        if (
                            "ValueError" not in clean_line
                            and "Traceback" not in clean_line
                        ):
                            print(f"  {clean_line}")

            process.wait(timeout=300)  # 5 min timeout per suburb

            if process.returncode == 0:
                log(f"✅ Finished {suburb}", style="green")
            else:
                log(
                    f"⚠️  Incomplete for {suburb} (Code {process.returncode})",
                    style="yellow",
                )

        except subprocess.TimeoutExpired:
            log(f"⏱️  Timeout for {suburb}, moving on...", style="yellow")
            if process:
                process.kill()
        except Exception as e:
            log(f"❌ Error processing {suburb}: {e}", style="red")

        # 4. Long random delay between suburbs
        if i < len(suburbs) - 1:
            delay = random.randint(20, 60)
            log(f"Random break: {delay}s...", style="dim")
            time.sleep(delay)

    run_vpn_command(["disconnect"], check=False)
    log("\n✨ Harvest Complete.", style="bold blue")


if __name__ == "__main__":
    main()
    main()
