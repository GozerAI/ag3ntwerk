#!/usr/bin/env python3
"""
ag3ntwerk Command Center Launcher

Starts both the FastAPI backend and the React frontend for the ag3ntwerk Command Center.

Usage:
    python run.py          # Start both backend and frontend
    python run.py --api    # Start only the API server
    python run.py --web    # Start only the web frontend (assumes API is running)
"""

import argparse
import asyncio
import os
import subprocess
import sys
import signal
import time
from pathlib import Path


# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_banner():
    """Print the ag3ntwerk banner."""
    banner = f"""{Colors.CYAN}
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   {Colors.BOLD}C-SUITE COMMAND CENTER{Colors.CYAN}                              ║
    ║   Your Unified Dashboard for All Affairs                  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    {Colors.ENDC}"""
    print(banner)


def find_project_root() -> Path:
    """Find the project root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


def check_dependencies():
    """Check if required dependencies are installed."""
    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print(f"{Colors.WARNING}Missing Python dependencies. Installing...{Colors.ENDC}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "pydantic"],
            check=True,
        )


def start_api_server(host: str = "127.0.0.1", port: int = 8000):
    """Start the FastAPI backend server."""
    print(f"{Colors.GREEN}Starting API server on http://{host}:{port}{Colors.ENDC}")
    print(f"{Colors.CYAN}  → API Docs: http://{host}:{port}/docs{Colors.ENDC}")

    # Add project paths to Python path
    project_root = find_project_root()
    csuite_src = project_root / "src" / "ag3ntwerk"
    nexus_src = project_root / "src" / "nexus" / "src"

    # Add to sys.path for this process
    if str(nexus_src) not in sys.path:
        sys.path.insert(0, str(nexus_src))
    if str(csuite_src) not in sys.path:
        sys.path.insert(0, str(csuite_src))

    # Also set PYTHONPATH for uvicorn's reloader subprocess
    python_path = os.environ.get("PYTHONPATH", "")
    paths = [str(nexus_src), str(csuite_src)]
    if python_path:
        paths.append(python_path)
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)

    print(f"{Colors.CYAN}  → PYTHONPATH: {os.environ['PYTHONPATH']}{Colors.ENDC}")

    # Change to the ag3ntwerk directory
    os.chdir(str(csuite_src))

    import uvicorn

    uvicorn.run(
        "ag3ntwerk.api.app:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[str(csuite_src), str(nexus_src)],
        log_level="info",
    )


def start_web_frontend():
    """Start the React frontend development server."""
    project_root = find_project_root()
    web_dir = project_root / "src" / "ag3ntwerk" / "web"

    if not web_dir.exists():
        print(f"{Colors.FAIL}Web directory not found: {web_dir}{Colors.ENDC}")
        return None

    # Check if node_modules exists
    if not (web_dir / "node_modules").exists():
        print(f"{Colors.WARNING}Installing npm dependencies...{Colors.ENDC}")
        subprocess.run(["npm", "install"], cwd=str(web_dir), check=True, shell=True)

    print(f"{Colors.GREEN}Starting web frontend on http://localhost:3000{Colors.ENDC}")

    # Start npm dev server
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(web_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main():
    parser = argparse.ArgumentParser(description="ag3ntwerk Command Center Launcher")
    parser.add_argument("--api", action="store_true", help="Start only the API server")
    parser.add_argument("--web", action="store_true", help="Start only the web frontend")
    parser.add_argument("--host", default="127.0.0.1", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    args = parser.parse_args()

    print_banner()
    check_dependencies()

    processes = []

    try:
        if args.api:
            # API only
            start_api_server(args.host, args.port)
        elif args.web:
            # Web only
            web_proc = start_web_frontend()
            if web_proc:
                processes.append(web_proc)
                web_proc.wait()
        else:
            # Both - start web in background, API in foreground
            print(f"\n{Colors.BOLD}Starting ag3ntwerk Command Center...{Colors.ENDC}\n")

            # Start web frontend first (in background)
            web_proc = start_web_frontend()
            if web_proc:
                processes.append(web_proc)

            # Give it a moment to start
            time.sleep(2)

            print(
                f"\n{Colors.BOLD}Dashboard available at: {Colors.GREEN}http://localhost:3000{Colors.ENDC}\n"
            )

            # Start API server (this blocks)
            start_api_server(args.host, args.port)

    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Shutting down...{Colors.ENDC}")
    finally:
        # Clean up any background processes
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                proc.kill()
        print(f"{Colors.GREEN}Goodbye!{Colors.ENDC}")


if __name__ == "__main__":
    main()
