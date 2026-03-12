"""
Framework Detector - Auto-detect project frameworks from manifest files.

Analyzes workspace files to determine the framework, build commands,
and optimal deployment configuration.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FrameworkType(str, Enum):
    """Detected framework types."""

    # Python frameworks
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    PYTHON_SCRIPT = "python_script"

    # Node.js frameworks
    NEXTJS = "nextjs"
    REACT = "react"
    VUE = "vue"
    NUXT = "nuxt"
    SVELTE = "svelte"
    EXPRESS = "express"
    NODEJS = "nodejs"

    # Go frameworks
    GIN = "gin"
    ECHO = "echo"
    FIBER = "fiber"
    GO_MODULE = "go_module"

    # Rust frameworks
    ACTIX = "actix"
    ROCKET = "rocket"
    AXUM = "axum"
    RUST_BIN = "rust_bin"

    # Static
    STATIC_SITE = "static_site"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class FrameworkInfo:
    """Detected framework information with deployment configuration."""

    framework: FrameworkType
    version: Optional[str] = None
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    install_command: Optional[str] = None
    output_directory: Optional[str] = None
    port: int = 3000
    environment_variables: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dockerfile_base: Optional[str] = None
    vercel_config: Dict[str, Any] = field(default_factory=dict)
    entry_point: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "framework": self.framework.value,
            "version": self.version,
            "build_command": self.build_command,
            "start_command": self.start_command,
            "install_command": self.install_command,
            "output_directory": self.output_directory,
            "port": self.port,
            "environment_variables": self.environment_variables,
            "dependencies": self.dependencies,
            "dockerfile_base": self.dockerfile_base,
            "vercel_config": self.vercel_config,
            "entry_point": self.entry_point,
        }


class FrameworkDetector:
    """
    Auto-detect project framework from manifest files.

    Detection priority:
    1. Check for specific framework configs (next.config.js, etc.)
    2. Parse package.json / requirements.txt / go.mod / Cargo.toml
    3. Analyze dependency list
    4. Fall back to file extension analysis

    Example:
        ```python
        detector = FrameworkDetector("/path/to/workspace")
        info = await detector.detect()
        print(f"Framework: {info.framework}")
        print(f"Build command: {info.build_command}")
        ```
    """

    def __init__(self, workspace_path: str):
        """
        Initialize the detector.

        Args:
            workspace_path: Path to the workspace directory
        """
        self._path = Path(workspace_path)

    async def detect(self) -> FrameworkInfo:
        """
        Detect framework and return configuration.

        Returns:
            FrameworkInfo with detected configuration
        """
        logger.debug(f"Detecting framework in {self._path}")

        # Check Node.js projects
        if (self._path / "package.json").exists():
            return await self._detect_nodejs()

        # Check Python projects
        if (
            (self._path / "requirements.txt").exists()
            or (self._path / "pyproject.toml").exists()
            or (self._path / "setup.py").exists()
        ):
            return await self._detect_python()

        # Check Go projects
        if (self._path / "go.mod").exists():
            return await self._detect_go()

        # Check Rust projects
        if (self._path / "Cargo.toml").exists():
            return await self._detect_rust()

        # Check for static site
        if (self._path / "index.html").exists():
            return self._static_site_config()

        logger.warning(f"Could not detect framework in {self._path}")
        return FrameworkInfo(framework=FrameworkType.UNKNOWN)

    async def _detect_nodejs(self) -> FrameworkInfo:
        """Detect Node.js framework from package.json."""
        pkg_path = self._path / "package.json"
        try:
            with open(pkg_path) as f:
                package = json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse package.json: {e}")
            return FrameworkInfo(framework=FrameworkType.NODEJS)

        deps = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
        scripts = package.get("scripts", {})

        # Next.js
        if "next" in deps:
            return FrameworkInfo(
                framework=FrameworkType.NEXTJS,
                version=deps.get("next"),
                build_command="npm run build",
                start_command="npm run start",
                install_command="npm install",
                output_directory=".next",
                port=3000,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "nextjs"},
                entry_point="pages/index.js",
            )

        # React (Create React App or Vite)
        if "react-scripts" in deps:
            return FrameworkInfo(
                framework=FrameworkType.REACT,
                version=deps.get("react"),
                build_command="npm run build",
                start_command="npx serve -s build -l 3000",
                install_command="npm install",
                output_directory="build",
                port=3000,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "create-react-app"},
            )

        if "vite" in deps and "react" in deps:
            return FrameworkInfo(
                framework=FrameworkType.REACT,
                version=deps.get("react"),
                build_command="npm run build",
                start_command="npx serve -s dist -l 3000",
                install_command="npm install",
                output_directory="dist",
                port=3000,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "vite"},
            )

        # Vue
        if "vue" in deps:
            output_dir = "dist"
            if "@vue/cli-service" in deps:
                output_dir = "dist"
            return FrameworkInfo(
                framework=FrameworkType.VUE,
                version=deps.get("vue"),
                build_command="npm run build",
                start_command="npx serve -s dist -l 8080",
                install_command="npm install",
                output_directory=output_dir,
                port=8080,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "vue"},
            )

        # Nuxt
        if "nuxt" in deps:
            return FrameworkInfo(
                framework=FrameworkType.NUXT,
                version=deps.get("nuxt"),
                build_command="npm run build",
                start_command="npm run start",
                install_command="npm install",
                output_directory=".output",
                port=3000,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "nuxt"},
            )

        # Svelte / SvelteKit
        if "svelte" in deps or "@sveltejs/kit" in deps:
            return FrameworkInfo(
                framework=FrameworkType.SVELTE,
                version=deps.get("svelte") or deps.get("@sveltejs/kit"),
                build_command="npm run build",
                start_command="npm run preview",
                install_command="npm install",
                output_directory="build",
                port=5173,
                dockerfile_base="node:20-alpine",
                vercel_config={"framework": "sveltekit"},
            )

        # Express
        if "express" in deps:
            start_cmd = scripts.get("start", "node index.js")
            entry = self._find_entry_point(["index.js", "app.js", "server.js", "src/index.js"])
            return FrameworkInfo(
                framework=FrameworkType.EXPRESS,
                version=deps.get("express"),
                build_command=scripts.get("build"),
                start_command=start_cmd,
                install_command="npm install",
                port=3000,
                dockerfile_base="node:20-alpine",
                entry_point=entry,
            )

        # Generic Node.js
        start_cmd = scripts.get("start", "node index.js")
        return FrameworkInfo(
            framework=FrameworkType.NODEJS,
            build_command=scripts.get("build"),
            start_command=start_cmd,
            install_command="npm install",
            port=3000,
            dockerfile_base="node:20-alpine",
        )

    async def _detect_python(self) -> FrameworkInfo:
        """Detect Python framework from requirements."""
        requirements = []

        # Read requirements.txt
        req_path = self._path / "requirements.txt"
        if req_path.exists():
            try:
                requirements = req_path.read_text().lower().splitlines()
            except Exception as e:
                logger.error(f"Failed to read requirements.txt: {e}")

        # Read pyproject.toml
        pyproject = self._path / "pyproject.toml"
        if pyproject.exists():
            try:
                # Use tomllib in Python 3.11+, fallback to basic parsing
                try:
                    import tomllib

                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                        deps = data.get("project", {}).get("dependencies", [])
                        requirements.extend([d.lower() for d in deps])
                except ImportError:
                    # Basic parsing for older Python
                    content = pyproject.read_text().lower()
                    requirements.append(content)
            except Exception as e:
                logger.error(f"Failed to parse pyproject.toml: {e}")

        reqs_str = " ".join(requirements)

        # FastAPI
        if "fastapi" in reqs_str:
            entry = self._find_entry_point(["main.py", "app.py", "api.py", "src/main.py"])
            module = entry.replace(".py", "").replace("/", ".") if entry else "main"
            return FrameworkInfo(
                framework=FrameworkType.FASTAPI,
                install_command="pip install -r requirements.txt",
                start_command=f"uvicorn {module}:app --host 0.0.0.0 --port 8000",
                port=8000,
                dockerfile_base="python:3.11-slim",
                entry_point=entry,
            )

        # Flask
        if "flask" in reqs_str:
            entry = self._find_entry_point(["app.py", "main.py", "wsgi.py", "src/app.py"])
            return FrameworkInfo(
                framework=FrameworkType.FLASK,
                install_command="pip install -r requirements.txt",
                start_command="gunicorn -w 4 -b 0.0.0.0:5000 app:app",
                port=5000,
                dockerfile_base="python:3.11-slim",
                entry_point=entry,
            )

        # Django
        if "django" in reqs_str:
            # Find Django project name from manage.py settings
            wsgi_module = self._find_django_wsgi()
            return FrameworkInfo(
                framework=FrameworkType.DJANGO,
                install_command="pip install -r requirements.txt",
                start_command=f"gunicorn -w 4 -b 0.0.0.0:8000 {wsgi_module}",
                build_command="python manage.py collectstatic --noinput",
                port=8000,
                dockerfile_base="python:3.11-slim",
            )

        # Generic Python
        entry = self._find_entry_point(["main.py", "app.py", "run.py"])
        return FrameworkInfo(
            framework=FrameworkType.PYTHON_SCRIPT,
            install_command="pip install -r requirements.txt" if req_path.exists() else None,
            start_command=f"python {entry or 'main.py'}",
            port=8000,
            dockerfile_base="python:3.11-slim",
            entry_point=entry,
        )

    async def _detect_go(self) -> FrameworkInfo:
        """Detect Go framework from go.mod."""
        try:
            go_mod = (self._path / "go.mod").read_text()
        except Exception as e:
            logger.error(f"Failed to read go.mod: {e}")
            go_mod = ""

        # Gin
        if "gin-gonic/gin" in go_mod:
            return FrameworkInfo(
                framework=FrameworkType.GIN,
                build_command="go build -o app .",
                start_command="./app",
                port=8080,
                dockerfile_base="golang:1.22-alpine",
            )

        # Echo
        if "labstack/echo" in go_mod:
            return FrameworkInfo(
                framework=FrameworkType.ECHO,
                build_command="go build -o app .",
                start_command="./app",
                port=8080,
                dockerfile_base="golang:1.22-alpine",
            )

        # Fiber
        if "gofiber/fiber" in go_mod:
            return FrameworkInfo(
                framework=FrameworkType.FIBER,
                build_command="go build -o app .",
                start_command="./app",
                port=3000,
                dockerfile_base="golang:1.22-alpine",
            )

        # Generic Go
        return FrameworkInfo(
            framework=FrameworkType.GO_MODULE,
            build_command="go build -o app .",
            start_command="./app",
            port=8080,
            dockerfile_base="golang:1.22-alpine",
        )

    async def _detect_rust(self) -> FrameworkInfo:
        """Detect Rust framework from Cargo.toml."""
        try:
            cargo_toml = (self._path / "Cargo.toml").read_text()
        except Exception as e:
            logger.error(f"Failed to read Cargo.toml: {e}")
            cargo_toml = ""

        # Get binary name from Cargo.toml
        binary_name = "app"
        try:
            for line in cargo_toml.splitlines():
                if line.strip().startswith("name"):
                    binary_name = line.split("=")[1].strip().strip('"').strip("'")
                    break
        except Exception as e:
            logger.debug("Failed to parse binary name from Cargo.toml: %s", e)

        # Actix-web
        if "actix-web" in cargo_toml:
            return FrameworkInfo(
                framework=FrameworkType.ACTIX,
                build_command="cargo build --release",
                start_command=f"./target/release/{binary_name}",
                port=8080,
                dockerfile_base="rust:1.77-slim",
            )

        # Rocket
        if "rocket" in cargo_toml:
            return FrameworkInfo(
                framework=FrameworkType.ROCKET,
                build_command="cargo build --release",
                start_command=f"./target/release/{binary_name}",
                port=8000,
                dockerfile_base="rust:1.77-slim",
            )

        # Axum
        if "axum" in cargo_toml:
            return FrameworkInfo(
                framework=FrameworkType.AXUM,
                build_command="cargo build --release",
                start_command=f"./target/release/{binary_name}",
                port=3000,
                dockerfile_base="rust:1.77-slim",
            )

        # Generic Rust
        return FrameworkInfo(
            framework=FrameworkType.RUST_BIN,
            build_command="cargo build --release",
            start_command=f"./target/release/{binary_name}",
            port=8080,
            dockerfile_base="rust:1.77-slim",
        )

    def _static_site_config(self) -> FrameworkInfo:
        """Configuration for static sites."""
        return FrameworkInfo(
            framework=FrameworkType.STATIC_SITE,
            build_command=None,
            start_command="npx serve -s . -l 3000",
            install_command="npm install -g serve",
            port=3000,
            dockerfile_base="node:20-alpine",
            vercel_config={"framework": None},
        )

    def _find_entry_point(self, candidates: List[str]) -> Optional[str]:
        """Find the first existing entry point file."""
        for candidate in candidates:
            if (self._path / candidate).exists():
                return candidate
        return None

    def _find_django_wsgi(self) -> str:
        """Find Django WSGI module from project structure."""
        # Look for settings.py to determine project name
        for item in self._path.iterdir():
            if item.is_dir():
                settings = item / "settings.py"
                wsgi = item / "wsgi.py"
                if settings.exists() or wsgi.exists():
                    return f"{item.name}.wsgi:application"

        return "project.wsgi:application"


async def detect_framework(workspace_path: str) -> FrameworkInfo:
    """
    Convenience function for framework detection.

    Args:
        workspace_path: Path to workspace directory

    Returns:
        FrameworkInfo with detected configuration
    """
    detector = FrameworkDetector(workspace_path)
    return await detector.detect()
