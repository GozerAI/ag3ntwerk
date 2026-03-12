#!/usr/bin/env python3
"""
ag3ntwerk Command Center - System Startup Script

This script provides a comprehensive startup for the ag3ntwerk system:
1. Checks all prerequisites (Python, dependencies, environment)
2. Starts Ollama (local LLM) if available
3. Initializes the Workbench service
4. Starts the FastAPI server
5. Verifies system health
6. Opens the dashboard in browser

Usage:
    python scripts/start_system.py [--no-browser] [--port 8000] [--host 0.0.0.0]
    python scripts/start_system.py --skip-ollama   # Skip Ollama startup
    python scripts/start_system.py --skip-workbench  # Skip Workbench initialization
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "nexus" / "src"))


def print_banner():
    """Print startup banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          C-SUITE COMMAND CENTER                           ║
    ║          Autonomous AI Agent System                   ║
    ║                                                           ║
    ╠═══════════════════════════════════════════════════════════╣
    ║                                                           ║
    ║  Components:                                              ║
    ║  • Nexus (Overwatch) - Central Orchestration               ║
    ║  • Autonomous Agenda Engine - Goal-Based Planning        ║
    ║  • 14 C-Level Agents - Domain Specialists            ║
    ║  • Human-in-the-Loop Security - Risk Management          ║
    ║  • Workbench - Development Environment Management        ║
    ║  • Ollama - Local LLM Inference                          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version():
    """Check Python version is 3.10+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check required packages are installed."""
    required = ["fastapi", "uvicorn", "pydantic"]
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False

    print("✓ Core dependencies installed")
    return True


def check_ag3ntwerk_imports():
    """Check ag3ntwerk modules can be imported."""
    try:
        from ag3ntwerk.api.app import app
        from ag3ntwerk.agenda import AutonomousAgendaEngine

        print("✓ ag3ntwerk modules available")
        return True
    except ImportError as e:
        print(f"❌ ag3ntwerk import error: {e}")
        return False


def check_environment():
    """Check environment configuration."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print("✓ Environment file (.env) found")
    else:
        print("⚠ No .env file - using defaults")

    # Check for LLM configuration
    llm_configured = any(
        [
            os.environ.get("OPENAI_API_KEY"),
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("OLLAMA_HOST"),
        ]
    )

    if llm_configured:
        print("✓ LLM provider configured")
    else:
        print("⚠ No LLM provider configured - will try Ollama")

    return True


def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ Ollama installed: {version}")
            return True
    except FileNotFoundError:
        print("⚠ Ollama not found in PATH")
    except subprocess.TimeoutExpired:
        print("⚠ Ollama check timed out")
    except Exception as e:
        print(f"⚠ Ollama check failed: {e}")
    return False


def check_docker_available():
    """Check if Docker is available for Workbench."""
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Docker available and running")
            return True
        else:
            # Docker daemon might not be running
            print("⚠ Docker installed but daemon not running")
            return False
    except FileNotFoundError:
        print("⚠ Docker not found in PATH")
    except subprocess.TimeoutExpired:
        print("⚠ Docker check timed out")
    except Exception as e:
        print(f"⚠ Docker check failed: {e}")
    return False


async def start_docker():
    """
    Start Docker Desktop if not running (Windows/macOS).

    Returns True if Docker becomes available.
    """
    import platform

    system = platform.system()

    print("\n⏳ Starting Docker...")

    if system == "Windows":
        # Try to start Docker Desktop on Windows
        docker_paths = [
            r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
            r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Docker\Docker\Docker Desktop.exe"),
        ]

        docker_exe = None
        for path in docker_paths:
            if os.path.exists(path):
                docker_exe = path
                break

        if docker_exe:
            try:
                # Start Docker Desktop without waiting
                subprocess.Popen(
                    [docker_exe],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                )
                print("  Starting Docker Desktop...")
            except Exception as e:
                print(f"  ⚠ Could not start Docker Desktop: {e}")
                return False
        else:
            print("  ⚠ Docker Desktop not found")
            return False

    elif system == "Darwin":  # macOS
        try:
            subprocess.Popen(
                ["open", "-a", "Docker"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("  Starting Docker Desktop...")
        except Exception as e:
            print(f"  ⚠ Could not start Docker: {e}")
            return False

    elif system == "Linux":
        # On Linux, try to start docker daemon via systemd
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "start", "docker"], capture_output=True, timeout=30
            )
            if result.returncode == 0:
                print("  Started Docker daemon via systemd")
            else:
                print("  ⚠ Could not start Docker daemon")
                return False
        except Exception as e:
            print(f"  ⚠ Could not start Docker daemon: {e}")
            return False

    # Wait for Docker to become available
    print("  Waiting for Docker to be ready...")
    for i in range(60):  # Wait up to 60 seconds
        await asyncio.sleep(1)
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if result.returncode == 0:
                print("✓ Docker is ready")
                return True
        except Exception:
            pass

        if i % 10 == 9:
            print(f"  Still waiting... ({i+1}s)")

    print("⚠ Docker did not become ready in time")
    return False


async def start_ollama():
    """Start Ollama if not already running."""
    try:
        from nexus.services.ollama_manager import OllamaManager, OllamaStatus

        manager = OllamaManager(
            host="http://localhost:11434",
            auto_start=True,
            startup_timeout=60.0,
        )

        print("\n⏳ Starting Ollama...")
        started = await manager.start()

        if started:
            print("✓ Ollama is running")

            # List available models
            models = await manager.get_models()
            if models:
                model_names = [m.get("name", "unknown") for m in models[:5]]
                print(f"  Available models: {', '.join(model_names)}")
                if len(models) > 5:
                    print(f"  ... and {len(models) - 5} more")
            else:
                print("  ⚠ No models installed - run 'ollama pull <model>' to add models")

            # Start health monitoring
            await manager.start_health_monitoring()
            return manager
        else:
            print("⚠ Could not start Ollama - continuing without local LLM")
            return None

    except ImportError as e:
        print(f"⚠ Ollama manager not available: {e}")
        return None
    except Exception as e:
        print(f"⚠ Error starting Ollama: {e}")
        return None


async def init_workbench():
    """Initialize the Workbench service."""
    try:
        from ag3ntwerk.modules.workbench.service import WorkbenchService, get_workbench_service

        print("\n⏳ Initializing Workbench...")
        service = get_workbench_service()
        await service.initialize()

        print("✓ Workbench initialized")
        print(f"  Runner type: {service._settings.runner_type}")
        print(f"  Root directory: {service._settings.get_root_path()}")

        return service

    except ImportError as e:
        print(f"⚠ Workbench module not available: {e}")
        return None
    except Exception as e:
        print(f"⚠ Error initializing Workbench: {e}")
        return None


async def wait_for_health(host: str, port: int, timeout: int = 30):
    """Wait for the server to become healthy."""
    import aiohttp

    url = f"http://{host}:{port}/health"
    start_time = time.time()

    print(f"\n⏳ Waiting for server health check...")

    while time.time() - start_time < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ Server healthy: {data.get('status', 'ok')}")
                        return True
        except Exception:
            pass

        await asyncio.sleep(1)
        print(".", end="", flush=True)

    print(f"\n❌ Server did not become healthy within {timeout}s")
    return False


async def check_agenda_engine(host: str, port: int):
    """Check if agenda engine is connected."""
    import aiohttp

    url = f"http://{host}:{port}/api/v1/coo/agenda"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("agenda_enabled"):
                        print("✓ Autonomous Agenda Engine connected")
                        return True
                    else:
                        print("⚠ Agenda engine not connected")
                        return False
    except Exception as e:
        print(f"⚠ Could not check agenda engine: {e}")
        return False


async def check_workbench_status(host: str, port: int):
    """Check if Workbench service is operational."""
    import aiohttp

    url = f"http://{host}:{port}/api/v1/workbench/workspaces"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    print("✓ Workbench service operational")
                    return True
                elif response.status == 404:
                    print("⚠ Workbench API not available (endpoints not registered)")
                    return False
                else:
                    print(f"⚠ Workbench returned status {response.status}")
                    return False
    except Exception as e:
        print(f"⚠ Could not check Workbench: {e}")
        return False


async def check_ollama_status(host: str, port: int):
    """Check Ollama status via the health endpoint."""
    import aiohttp

    # Check directly with Ollama API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    if models:
                        print(f"✓ Ollama running with {len(models)} model(s)")
                    else:
                        print("✓ Ollama running (no models loaded)")
                    return True
                else:
                    print(f"⚠ Ollama returned status {response.status}")
                    return False
    except Exception as e:
        print(f"⚠ Ollama not reachable: {e}")
        return False


def start_server(host: str, port: int, reload: bool = True):
    """Start the uvicorn server."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "ag3ntwerk.api.app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    if reload:
        cmd.append("--reload")

    print(f"\n🚀 Starting server on http://{host}:{port}")
    print("   Press Ctrl+C to stop\n")
    print("=" * 60)

    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT / "src"))


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start ag3ntwerk Command Center")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama startup")
    parser.add_argument(
        "--skip-workbench", action="store_true", help="Skip Workbench initialization"
    )
    args = parser.parse_args()

    print_banner()

    print("Checking prerequisites...\n")

    # Run checks
    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("ag3ntwerk modules", check_ag3ntwerk_imports),
        ("Environment", check_environment),
    ]

    all_passed = True
    for name, check_fn in checks:
        if not check_fn():
            all_passed = False

    if not all_passed:
        print("\n❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

    # Check optional components
    ollama_available = check_ollama_installed()
    docker_available = check_docker_available()

    print("\n" + "=" * 60)

    # Start services in the right order
    ollama_manager = None
    workbench_service = None

    # 1. Start Docker first (needed for Workbench)
    if not docker_available and not args.skip_workbench:
        docker_available = await start_docker()

    # 2. Start Ollama (for local LLM)
    if ollama_available and not args.skip_ollama:
        ollama_manager = await start_ollama()
    elif not ollama_available and not args.skip_ollama:
        # Try to start Ollama anyway in case it's just not responding
        print("\n⏳ Attempting to start Ollama...")
        ollama_manager = await start_ollama()

    # 3. Initialize Workbench (uses Docker)
    if docker_available and not args.skip_workbench:
        workbench_service = await init_workbench()
    elif not args.skip_workbench:
        print("⚠ Skipping Workbench - Docker not available")

    print("\n" + "=" * 60)

    # Start server
    server_process = start_server(args.host, args.port, not args.no_reload)

    try:
        # Wait for server to be healthy
        await asyncio.sleep(3)  # Give it time to start

        try:
            import aiohttp

            healthy = await wait_for_health(args.host, args.port)

            if healthy:
                await check_agenda_engine(args.host, args.port)
                await check_workbench_status(args.host, args.port)
                await check_ollama_status(args.host, args.port)

                if not args.no_browser:
                    url = f"http://localhost:{args.port}/"
                    print(f"\n🌐 Opening browser: {url}")
                    webbrowser.open(url)

                print("\n" + "=" * 60)
                print("\n📍 Access Points:")
                print(f"   • Dashboard:   http://localhost:{args.port}/")
                print(f"   • API Docs:    http://localhost:{args.port}/docs")
                print(f"   • Health:      http://localhost:{args.port}/health")
                print(f"   • Nexus Status:  http://localhost:{args.port}/api/v1/coo/status")
                print(f"   • Agenda:      http://localhost:{args.port}/api/v1/coo/agenda")
                print(f"   • Suggestions: http://localhost:{args.port}/api/v1/coo/suggestions")
                print(f"   • Workbench:   http://localhost:{args.port}/api/v1/workbench/workspaces")
                if ollama_manager:
                    print(f"   • Ollama:      http://localhost:11434/api/tags")
                print("\n" + "=" * 60 + "\n")

        except ImportError:
            print("⚠ aiohttp not installed - skipping health checks")
            print("  Install with: pip install aiohttp")

        # Wait for server process
        server_process.wait()

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")

        # Stop Ollama if we started it
        if ollama_manager:
            print("  Stopping Ollama health monitoring...")
            await ollama_manager.stop_health_monitoring()
            # Note: We don't stop Ollama itself - it can continue running

        # Shutdown workbench
        if workbench_service:
            print("  Shutting down Workbench...")
            await workbench_service.shutdown()

        server_process.terminate()
        server_process.wait()
        print("✓ Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
