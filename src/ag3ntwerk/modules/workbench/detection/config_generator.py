"""
Config Generator - Generate deployment configuration files.

Generates Dockerfile, vercel.json, and .env files based on detected framework.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.workbench.detection.framework_detector import (
    FrameworkInfo,
    FrameworkType,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratedConfigs:
    """Generated configuration files."""

    dockerfile: Optional[str] = None
    dockerignore: Optional[str] = None
    vercel_json: Optional[str] = None
    env_file: Optional[str] = None
    files_written: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "dockerfile": self.dockerfile is not None,
            "dockerignore": self.dockerignore is not None,
            "vercel_json": self.vercel_json is not None,
            "env_file": self.env_file is not None,
            "files_written": self.files_written,
        }


class ConfigGenerator:
    """
    Generate deployment configuration files based on detected framework.

    Generates:
    - Dockerfile (framework-specific multi-stage builds)
    - .dockerignore
    - vercel.json (for Vercel deployments)
    - .env from .env.example

    Example:
        ```python
        from ag3ntwerk.modules.workbench.detection import FrameworkDetector, ConfigGenerator

        detector = FrameworkDetector("/path/to/workspace")
        info = await detector.detect()

        generator = ConfigGenerator("/path/to/workspace", info)
        configs = await generator.generate_all(write_files=True)
        print(f"Files written: {configs.files_written}")
        ```
    """

    def __init__(self, workspace_path: str, framework_info: FrameworkInfo):
        """
        Initialize the generator.

        Args:
            workspace_path: Path to workspace directory
            framework_info: Detected framework information
        """
        self._path = Path(workspace_path)
        self._info = framework_info

    async def generate_all(
        self,
        write_files: bool = True,
        force: bool = False,
    ) -> GeneratedConfigs:
        """
        Generate all applicable config files.

        Args:
            write_files: Whether to write files to disk
            force: Overwrite existing files

        Returns:
            GeneratedConfigs with generated content
        """
        configs = GeneratedConfigs()

        # Generate Dockerfile
        if not (self._path / "Dockerfile").exists() or force:
            configs.dockerfile = self._generate_dockerfile()
            if write_files and configs.dockerfile:
                (self._path / "Dockerfile").write_text(configs.dockerfile)
                configs.files_written.append("Dockerfile")
                logger.info(f"Generated Dockerfile for {self._info.framework.value}")

        # Generate .dockerignore
        if not (self._path / ".dockerignore").exists() or force:
            configs.dockerignore = self._generate_dockerignore()
            if write_files and configs.dockerignore:
                (self._path / ".dockerignore").write_text(configs.dockerignore)
                configs.files_written.append(".dockerignore")

        # Generate vercel.json
        if self._should_generate_vercel():
            if not (self._path / "vercel.json").exists() or force:
                configs.vercel_json = self._generate_vercel_json()
                if write_files and configs.vercel_json:
                    (self._path / "vercel.json").write_text(configs.vercel_json)
                    configs.files_written.append("vercel.json")
                    logger.info("Generated vercel.json")

        # Generate .env from .env.example
        if (self._path / ".env.example").exists():
            if not (self._path / ".env").exists() or force:
                configs.env_file = self._generate_env_file()
                if write_files and configs.env_file:
                    (self._path / ".env").write_text(configs.env_file)
                    configs.files_written.append(".env")
                    logger.info("Generated .env from .env.example")

        return configs

    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile based on framework."""
        info = self._info

        # Node.js with build step (Next.js, React, Vue, etc.)
        if info.framework in [
            FrameworkType.NEXTJS,
            FrameworkType.REACT,
            FrameworkType.VUE,
            FrameworkType.NUXT,
            FrameworkType.SVELTE,
        ]:
            return self._dockerfile_node_build()

        # Node.js runtime (Express, etc.)
        if info.framework in [FrameworkType.EXPRESS, FrameworkType.NODEJS]:
            return self._dockerfile_node_runtime()

        # Python
        if info.framework in [
            FrameworkType.FASTAPI,
            FrameworkType.FLASK,
            FrameworkType.DJANGO,
            FrameworkType.PYTHON_SCRIPT,
        ]:
            return self._dockerfile_python()

        # Go
        if info.framework in [
            FrameworkType.GIN,
            FrameworkType.ECHO,
            FrameworkType.FIBER,
            FrameworkType.GO_MODULE,
        ]:
            return self._dockerfile_go()

        # Rust
        if info.framework in [
            FrameworkType.ACTIX,
            FrameworkType.ROCKET,
            FrameworkType.AXUM,
            FrameworkType.RUST_BIN,
        ]:
            return self._dockerfile_rust()

        # Static site
        if info.framework == FrameworkType.STATIC_SITE:
            return self._dockerfile_static()

        return self._dockerfile_generic()

    def _dockerfile_node_build(self) -> str:
        """Dockerfile for Node.js apps with build step."""
        info = self._info
        output_dir = info.output_directory or "dist"

        # Special handling for Next.js standalone output
        if info.framework == FrameworkType.NEXTJS:
            return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN {info.build_command or "npm run build"}

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE {info.port}
ENV PORT={info.port}
CMD ["node", "server.js"]
"""

        # Generic Node.js build (React, Vue, etc.)
        return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN {info.build_command or "npm run build"}

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Install serve for static file serving
RUN npm install -g serve

COPY --from=builder /app/{output_dir} ./{output_dir}

EXPOSE {info.port}
CMD ["serve", "-s", "{output_dir}", "-l", "{info.port}"]
"""

    def _dockerfile_node_runtime(self) -> str:
        """Dockerfile for Node.js runtime apps."""
        info = self._info
        return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM node:20-alpine
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

ENV NODE_ENV=production
EXPOSE {info.port}

CMD {json.dumps(info.start_command.split() if info.start_command else ["node", "index.js"])}
"""

    def _dockerfile_python(self) -> str:
        """Dockerfile for Python apps."""
        info = self._info

        # Add specific dependencies based on framework
        extra_deps = ""
        if info.framework == FrameworkType.FASTAPI:
            extra_deps = "uvicorn[standard]"
        elif info.framework in [FrameworkType.FLASK, FrameworkType.DJANGO]:
            extra_deps = "gunicorn"

        return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM {info.dockerfile_base or "python:3.11-slim"}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt{" " + extra_deps if extra_deps else ""}

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE {info.port}
CMD {json.dumps(info.start_command.split() if info.start_command else ["python", "main.py"])}
"""

    def _dockerfile_go(self) -> str:
        """Dockerfile for Go apps."""
        info = self._info
        return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM {info.dockerfile_base or "golang:1.22-alpine"} AS builder

WORKDIR /app

# Download dependencies
COPY go.mod go.sum* ./
RUN go mod download

# Copy source and build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux {info.build_command or "go build -o app ."}

# Runtime image
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata
WORKDIR /app

COPY --from=builder /app/app .

EXPOSE {info.port}
CMD ["./app"]
"""

    def _dockerfile_rust(self) -> str:
        """Dockerfile for Rust apps."""
        info = self._info

        # Extract binary name from start command
        binary_name = "app"
        if info.start_command:
            parts = info.start_command.split("/")
            if parts:
                binary_name = parts[-1]

        return f"""# Generated by ag3ntwerk Workbench
# Framework: {info.framework.value}

FROM {info.dockerfile_base or "rust:1.77-slim"} AS builder

WORKDIR /app
COPY . .

# Build release binary
RUN {info.build_command or "cargo build --release"}

# Runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/{binary_name} .

EXPOSE {info.port}
CMD ["./{binary_name}"]
"""

    def _dockerfile_static(self) -> str:
        """Dockerfile for static sites."""
        return f"""# Generated by ag3ntwerk Workbench
# Static site

FROM node:20-alpine

WORKDIR /app

# Install serve
RUN npm install -g serve

# Copy static files
COPY . .

EXPOSE {self._info.port}
CMD ["serve", "-s", ".", "-l", "{self._info.port}"]
"""

    def _dockerfile_generic(self) -> str:
        """Generic Dockerfile fallback."""
        return """# Generated by ag3ntwerk Workbench
# Generic container

FROM alpine:latest
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["sh"]
"""

    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore file."""
        ignore_patterns = [
            "# Dependencies",
            "node_modules/",
            ".pnp/",
            ".pnp.js",
            "__pycache__/",
            "*.py[cod]",
            "venv/",
            ".venv/",
            "target/",
            "",
            "# Build outputs",
            ".next/",
            "out/",
            "build/",
            "dist/",
            "*.egg-info/",
            "",
            "# Testing",
            "coverage/",
            ".nyc_output/",
            ".pytest_cache/",
            "",
            "# IDE and editor",
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            "",
            "# Git",
            ".git/",
            ".gitignore",
            "",
            "# Docker",
            "Dockerfile*",
            ".dockerignore",
            "docker-compose*.yml",
            "",
            "# Environment",
            ".env*",
            "!.env.example",
            "",
            "# Misc",
            "*.log",
            "*.md",
            "README*",
            "LICENSE*",
            ".DS_Store",
            "Thumbs.db",
        ]
        return "\n".join(ignore_patterns)

    def _should_generate_vercel(self) -> bool:
        """Check if vercel.json should be generated."""
        vercel_frameworks = [
            FrameworkType.NEXTJS,
            FrameworkType.REACT,
            FrameworkType.VUE,
            FrameworkType.NUXT,
            FrameworkType.SVELTE,
            FrameworkType.EXPRESS,
            FrameworkType.NODEJS,
            FrameworkType.STATIC_SITE,
        ]
        return self._info.framework in vercel_frameworks

    def _generate_vercel_json(self) -> str:
        """Generate vercel.json configuration."""
        config: Dict[str, Any] = {
            "$schema": "https://openapi.vercel.sh/vercel.json",
        }

        # Set framework
        if self._info.vercel_config.get("framework"):
            config["framework"] = self._info.vercel_config["framework"]

        # Build settings
        if self._info.build_command:
            config["buildCommand"] = self._info.build_command

        if self._info.output_directory:
            config["outputDirectory"] = self._info.output_directory

        if self._info.install_command:
            config["installCommand"] = self._info.install_command

        # Environment variables
        if self._info.environment_variables:
            config["env"] = self._info.environment_variables

        return json.dumps(config, indent=2)

    def _generate_env_file(self) -> str:
        """Generate .env from .env.example with placeholder values."""
        example_path = self._path / ".env.example"
        if not example_path.exists():
            return ""

        try:
            lines = example_path.read_text().splitlines()
        except Exception as e:
            logger.error(f"Failed to read .env.example: {e}")
            return ""

        result = []
        for line in lines:
            line = line.strip()

            # Keep comments
            if line.startswith("#") or not line:
                result.append(line)
                continue

            # Process key=value pairs
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()

                # Keep existing values, add placeholder if empty
                if value:
                    result.append(f"{key}={value}")
                else:
                    # Generate placeholder based on key name
                    placeholder = self._generate_placeholder(key)
                    result.append(f"{key}={placeholder}")
            else:
                result.append(line)

        return "\n".join(result)

    def _generate_placeholder(self, key: str) -> str:
        """Generate a placeholder value based on key name."""
        key_lower = key.lower()

        # URLs
        if "url" in key_lower or "uri" in key_lower:
            if "database" in key_lower or "db" in key_lower:
                return "postgresql://user:password@localhost:5432/dbname"
            if "redis" in key_lower:
                return "redis://localhost:6379"
            return "http://localhost:3000"

        # Ports
        if "port" in key_lower:
            return "3000"

        # Hosts
        if "host" in key_lower:
            return "localhost"

        # Secrets and keys
        if any(x in key_lower for x in ["secret", "key", "token", "password"]):
            return "your-secret-key-here"

        # Booleans
        if any(x in key_lower for x in ["enable", "disable", "debug", "is_"]):
            return "false"

        # Default
        return f"your-{key_lower.replace('_', '-')}-here"
