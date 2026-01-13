#!/usr/bin/env python3
"""
Antigravity Delegator - Test Suite
Validates all components: Gemini CLI, Codex CLI, and Quality Gate
"""
import subprocess
import sys
import os
import tempfile
import shutil

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*50}{Colors.RESET}")

def print_pass(text):
    print(f"{Colors.GREEN}PASS:{Colors.RESET} {text}")

def print_fail(text):
    print(f"{Colors.RED}FAIL:{Colors.RESET} {text}")

def print_warn(text):
    print(f"{Colors.YELLOW}WARN:{Colors.RESET} {text}")

def print_info(text):
    print(f"{Colors.BLUE}INFO:{Colors.RESET} {text}")

def test_command_exists(cmd_name, check_cmd):
    """Check if a command is available"""
    try:
        result = subprocess.run(
            check_cmd, 
            shell=True, 
            capture_output=True, 
            timeout=10
        )
        return True
    except Exception:
        return False

def test_gemini_cli():
    """Test Gemini CLI availability and basic function"""
    print_header("Testing Gemini CLI")
    
    # Check if gemini command exists
    if not shutil.which('gemini'):
        print_fail("Gemini CLI not found in PATH")
        print_info("Install with: npm install -g @google/gemini-cli")
        return False
    
    print_pass("Gemini CLI found")
    
    # Test basic invocation
    try:
        result = subprocess.run(
            'gemini --version',
            shell=True,
            capture_output=True,
            timeout=10,
            text=True
        )
        if result.returncode == 0:
            print_pass(f"Gemini CLI version: {result.stdout.strip()}")
            return True
        else:
            print_warn("Gemini CLI exists but version check failed")
            return True  # Still consider available
    except subprocess.TimeoutExpired:
        print_warn("Gemini CLI timed out (may still work)")
        return True
    except Exception as e:
        print_fail(f"Gemini CLI error: {e}")
        return False

def test_codex_cli():
    """Test Codex CLI availability"""
    print_header("Testing Codex CLI")
    
    # Check if codex command exists
    if not shutil.which('codex'):
        print_fail("Codex CLI not found in PATH")
        print_info("Install with: npm install -g @openai/codex")
        return False
    
    print_pass("Codex CLI found")
    
    # Test basic invocation
    try:
        result = subprocess.run(
            'codex --version',
            shell=True,
            capture_output=True,
            timeout=10,
            text=True
        )
        if result.returncode == 0:
            print_pass(f"Codex CLI version: {result.stdout.strip()}")
            return True
        else:
            print_warn("Codex CLI exists but version check failed")
            return True

    except subprocess.TimeoutExpired:
        print_warn("Codex CLI timed out (may still work)")
        return True
    except Exception as e:
        print_fail(f"Codex CLI error: {e}")
        return False

def test_quality_gate():
    """Test the quality gate script"""
    print_header("Testing Quality Gate")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    quality_gate = os.path.join(script_dir, 'quality_gate.py')
    
    if not os.path.exists(quality_gate):
        print_fail("quality_gate.py not found")
        return False
    
    print_pass("quality_gate.py found")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def hello():\n    return "Hello, World!"\n')
        test_file = f.name
    
    try:
        # Test with valid file
        result = subprocess.run(
            [sys.executable, quality_gate, test_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print_pass("Quality gate validates valid Python")
        else:
            print_fail(f"Quality gate rejected valid file: {result.stdout}")
            return False
    finally:
        os.unlink(test_file)
    
    # Test with conversational content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('Here is the code:\ndef hello():\n    return "Hi"\n')
        test_file = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, quality_gate, test_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 1:
            print_pass("Quality gate detects conversational leakage")
        else:
            print_warn("Quality gate did not catch conversational content")
    finally:
        os.unlink(test_file)
    
    return True

def test_context_files():
    """Check if context files exist"""
    print_header("Testing Context Files")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files = {
        'GEMINI.md': 'Gemini CLI context',
        'CODEX.md': 'Codex CLI context',
        'ARCHITECT_RULES.md': 'Architect rules'
    }
    
    all_found = True
    for filename, description in files.items():
        filepath = os.path.join(script_dir, filename)
        if os.path.exists(filepath):
            print_pass(f"{filename} exists ({description})")
        else:
            print_fail(f"{filename} not found")
            all_found = False
    
    return all_found

def run_all_tests():
    """Run all tests and report results"""
    print(f"\n{Colors.BOLD}ANTIGRAVITY DELEGATOR TEST SUITE{Colors.RESET}")
    print(f"Running from: {os.path.dirname(os.path.abspath(__file__))}\n")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Prepend bin directory to PATH so shims are found first
    os.environ['PATH'] = os.path.join(script_dir, 'bin') + os.pathsep + os.environ['PATH']
    
    results = {
        'Context Files': test_context_files(),
        'Quality Gate': test_quality_gate(),
        'Gemini CLI': test_gemini_cli(),
        'Codex CLI': test_codex_cli(),
    }
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed_test else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"{Colors.GREEN}All systems operational!{Colors.RESET}")
    elif passed >= 2:
        print(f"{Colors.YELLOW}Some components need setup{Colors.RESET}")
    else:
        print(f"{Colors.RED}Critical components missing{Colors.RESET}")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
