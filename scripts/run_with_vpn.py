import subprocess
import time
import random
import sys
import os
import datetime
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
    "219": "Woolloomooloo"
}

# Config
LOG_FILE = "scanner.log"

def log(text, style=None):
    """
    Dual-logging: Print to Rich console and append to LOG_FILE.
    Handles Rich formatting for console, but strips it (crudely) or logs raw text for file.
    Since 'text' here might contain Rich markup (e.g. [bold]), for simple file logging
    we rely on the user reading the raw text or we assume the text is readable.
    """
    # 1. Print to Terminal
    if style:
        console.print(text, style=style)
    else:
        console.print(text)

    # 2. Append to File (Timestamped)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Strip basic Rich markup for the log file if simple, 
    # but for now we just log the raw string which is fine for VS Code reading.
    # A cleaner approach would be 'console.file.write', but manual is robust here.
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            # We assume 'text' is a string. If it has rich tags, they appear in log.
            f.write(f"[{timestamp}] {text}\n")
    except Exception as e:
        console.print(f"[red]Logging failed:[/red] {e}")

def run_vpn_command(args, check=True):
    """Run an ExpressVPN CLI command."""
    cmd = [VPN_CLI] + args
    try:
        # We capture output to log it
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=check,
            cwd=os.getcwd()
        )
        # Log stdout if any (useful for 'connect' success msg)
        if result.stdout.strip():
            log(f"VPN OUT: {result.stdout.strip()}", style="dim")
        return result
    except subprocess.CalledProcessError as e:
        log(f"VPN Command Failed: {e}", style="red")
        log(f"Stderr: {e.stderr}", style="red")
        return None
    except FileNotFoundError:
        log(f"VPN CLI not found at: {VPN_CLI}", style="red")
        sys.exit(1)

def run_scanner_stream(cmd):
    """Run the scanner subprocess and stream output to log + console."""
    # Use Popen to stream stdout
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Merge stderr into stdout
        text=True,
        bufsize=1, # Line buffered
        encoding='utf-8',
        cwd=os.getcwd()
    )
    
    # Read line by line
    with open(LOG_FILE, "a", encoding="utf-8") as logf:
        for line in process.stdout:
            line_clean = line.rstrip()
            
            # Print to console (direct print to avoid buffering/rich interference on raw output)
            print(line_clean)
            
            # Write to log
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            logf.write(f"[{timestamp}] {line_clean}\n")
            logf.flush() # Ensure it's written immediately for 'tail'
            
    returncode = process.wait()
    return returncode

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="VPN Scanner Wrapper")
    parser.add_argument("--loops", type=int, default=1, help="Number of batches to run")
    parser.add_argument("--source", default="random", help="Source to scrape")
    args, unknown_args = parser.parse_known_args()
    
    # Clear or Start Log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "="*50 + "\n")
        f.write(f"SESSION START: {datetime.datetime.now()}\n")
        f.write("="*50 + "\n")

    log("🛡️  Secure Scanner Launcher", style="bold blue")
    log(f"Targeting {args.loops} batches with source: {args.source}")
    log(f"Logging to: {os.path.abspath(LOG_FILE)}")
    
    scanner_script = Path(__file__).parent / "weekly_refresh_ldrz.py"
    
    for i in range(1, args.loops + 1):
        log(f"\n=== Batch {i}/{args.loops} ===", style="bold magenta")
        
        # 1. Disconnect current session
        log("Disconnecting/Resetting VPN...", style="dim")
        run_vpn_command(["disconnect"], check=False)
        time.sleep(2)

        # 2. Pick a random location
        loc_id = random.choice(list(AU_LOCATIONS.keys()))
        loc_name = AU_LOCATIONS[loc_id]
        
        log(f"Connecting to ExpressVPN: {loc_name} (ID: {loc_id})", style="bold yellow")
        
        # 3. Connect
        result = run_vpn_command(["connect", loc_id])
        
        if result and result.returncode == 0:
            log(f"Successfully connected to {loc_name}!", style="green")
            log("Waiting 15 seconds for DNS/Routing to stabilize...", style="dim")
            time.sleep(15)
        else:
            log("Failed to connect to VPN. Aborting loop for safety.", style="red")
            break

        # 4. Run the scanner
        log("\n🚀 Launching Scanner...", style="bold")
        
        # Point to the optimized suburb list by default
        suburbs_file = Path(__file__).parent.parent / "config" / "suburbs_ldrz_feasible.txt"
        
        cmd = [
            sys.executable, 
            str(scanner_script), 
            "--source", args.source,
            "--suburbs-file", str(suburbs_file)
        ] + unknown_args
        
        try:
            # Replaced simple subprocess.run with streaming handler
            rc = run_scanner_stream(cmd)
            
            if rc == 0:
                log(f"Batch {i} complete!", style="green")
            else:
                log(f"Scanner script failed with exit code {rc}", style="red")
                
        except KeyboardInterrupt:
            log("\nInterrupted by user.", style="yellow")
            break
        except Exception as e:
            log(f"\nCritical Error: {e}", style="red")
            break
            
        # 5. Delay between loops (if not the last one)
        if i < args.loops:
            delay = random.randint(60, 180) # 1 to 3 minutes
            log(f"\nSleeping for {delay} seconds to randomize behavior...", style="bold cyan")
            time.sleep(delay)
            
    # Cleanup
    log("\nLoop Complete. Disconnecting...", style="bold")
    run_vpn_command(["disconnect"], check=False)

if __name__ == "__main__":
    main()
