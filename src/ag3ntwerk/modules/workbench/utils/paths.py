"""
Workbench Path Utilities - Workspace directory management.

Provides functions for creating, managing, and cleaning workspace directories.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from ag3ntwerk.modules.workbench.schemas import WorkspaceTemplate, RuntimeType
from ag3ntwerk.modules.workbench.settings import get_workbench_settings

logger = logging.getLogger(__name__)


def ensure_workspace_dir(workspace_id: str) -> Path:
    """
    Ensure the workspace directory exists.

    Creates the directory if it doesn't exist.

    Args:
        workspace_id: The workspace identifier.

    Returns:
        Path to the workspace directory.
    """
    settings = get_workbench_settings()
    workspace_path = settings.get_workspace_path(workspace_id)

    workspace_path.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Ensured workspace directory: {workspace_path}")
    return workspace_path


def get_workspace_path(workspace_id: str) -> Path:
    """
    Get the path for a workspace.

    Args:
        workspace_id: The workspace identifier.

    Returns:
        Path to the workspace directory.
    """
    settings = get_workbench_settings()
    return settings.get_workspace_path(workspace_id)


def init_workspace_from_template(
    workspace_id: str,
    template: WorkspaceTemplate,
    runtime: RuntimeType,
) -> Path:
    """
    Initialize a workspace from a template.

    Creates the workspace directory and populates it with
    template files based on the runtime type.

    Args:
        workspace_id: The workspace identifier.
        template: The template to use.
        runtime: The runtime type.

    Returns:
        Path to the initialized workspace directory.
    """
    workspace_path = ensure_workspace_dir(workspace_id)

    if template == WorkspaceTemplate.EMPTY:
        # Just create a .gitkeep
        (workspace_path / ".gitkeep").touch()
        return workspace_path

    # Template content based on runtime
    if runtime == RuntimeType.PYTHON:
        _init_python_workspace(workspace_path, template)
    elif runtime == RuntimeType.NODE:
        _init_node_workspace(workspace_path, template)
    elif runtime == RuntimeType.GO:
        _init_go_workspace(workspace_path, template)
    elif runtime == RuntimeType.RUST:
        _init_rust_workspace(workspace_path, template)

    logger.info(f"Initialized workspace {workspace_id} with template {template.value}")
    return workspace_path


def _init_python_workspace(workspace_path: Path, template: WorkspaceTemplate) -> None:
    """Initialize a Python workspace."""
    # Create main.py
    main_py = workspace_path / "main.py"
    main_py.write_text(
        '''"""
Main entry point for the application.
"""


def main():
    """Main function."""
    print("Hello from ag3ntwerk Workbench!")


if __name__ == "__main__":
    main()
'''
    )

    # Create requirements.txt
    requirements_txt = workspace_path / "requirements.txt"
    requirements_txt.write_text(
        """# Project dependencies
# Add your dependencies here
"""
    )

    # Create .gitignore
    gitignore = workspace_path / ".gitignore"
    gitignore.write_text(
        """# Python
__pycache__/
*.py[cod]
*$py.class
.Python
.venv/
venv/
ENV/
env/
.env

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Distribution
dist/
build/
*.egg-info/
"""
    )

    # Create setup script
    setup_sh = workspace_path / "setup.sh"
    setup_sh.write_text(
        """#!/bin/bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
"""
    )
    setup_sh.chmod(0o755)


def _init_node_workspace(workspace_path: Path, template: WorkspaceTemplate) -> None:
    """Initialize a Node.js workspace."""
    # Create package.json
    package_json = workspace_path / "package.json"
    package_json.write_text(
        """{
  "name": "ag3ntwerk-workspace",
  "version": "1.0.0",
  "description": "ag3ntwerk Workbench project",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \\"Error: no test specified\\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "MIT"
}
"""
    )

    # Create index.js
    index_js = workspace_path / "index.js"
    index_js.write_text(
        """/**
 * Main entry point for the application.
 */

function main() {
    console.log("Hello from ag3ntwerk Workbench!");
}

main();
"""
    )

    # Create .gitignore
    gitignore = workspace_path / ".gitignore"
    gitignore.write_text(
        """# Dependencies
node_modules/

# Build output
dist/
build/

# IDE
.idea/
.vscode/
*.swp

# Logs
logs/
*.log
npm-debug.log*

# Environment
.env
.env.local
"""
    )


def _init_go_workspace(workspace_path: Path, template: WorkspaceTemplate) -> None:
    """Initialize a Go workspace."""
    # Create go.mod
    go_mod = workspace_path / "go.mod"
    go_mod.write_text(
        """module workspace

go 1.22
"""
    )

    # Create main.go
    main_go = workspace_path / "main.go"
    main_go.write_text(
        """package main

import "fmt"

func main() {
	fmt.Println("Hello from ag3ntwerk Workbench!")
}
"""
    )

    # Create .gitignore
    gitignore = workspace_path / ".gitignore"
    gitignore.write_text(
        """# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
/workspace

# Test binary
*.test

# Output of the go coverage tool
*.out

# IDE
.idea/
.vscode/
*.swp
"""
    )


def _init_rust_workspace(workspace_path: Path, template: WorkspaceTemplate) -> None:
    """Initialize a Rust workspace."""
    # Create Cargo.toml
    cargo_toml = workspace_path / "Cargo.toml"
    cargo_toml.write_text(
        """[package]
name = "workspace"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
    )

    # Create src directory
    src_dir = workspace_path / "src"
    src_dir.mkdir(exist_ok=True)

    # Create main.rs
    main_rs = src_dir / "main.rs"
    main_rs.write_text(
        """fn main() {
    println!("Hello from ag3ntwerk Workbench!");
}
"""
    )

    # Create .gitignore
    gitignore = workspace_path / ".gitignore"
    gitignore.write_text(
        """# Build output
/target/

# IDE
.idea/
.vscode/
*.swp

# Cargo lock (optional, depends on if it's a lib or bin)
# Cargo.lock
"""
    )


def clean_workspace(workspace_id: str) -> bool:
    """
    Clean up a workspace directory.

    Removes the workspace directory and all its contents.

    Args:
        workspace_id: The workspace identifier.

    Returns:
        True if cleanup was successful.
    """
    settings = get_workbench_settings()
    workspace_path = settings.get_workspace_path(workspace_id)

    if not workspace_path.exists():
        return True

    try:
        shutil.rmtree(workspace_path)
        logger.info(f"Cleaned workspace directory: {workspace_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to clean workspace {workspace_id}: {e}")
        return False


def get_workspace_size(workspace_id: str) -> int:
    """
    Get the total size of a workspace in bytes.

    Args:
        workspace_id: The workspace identifier.

    Returns:
        Total size in bytes.
    """
    settings = get_workbench_settings()
    workspace_path = settings.get_workspace_path(workspace_id)

    if not workspace_path.exists():
        return 0

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(workspace_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, IOError):
                pass

    return total_size


def list_workspace_files(
    workspace_id: str,
    pattern: str = "**/*",
    max_depth: Optional[int] = None,
) -> list:
    """
    List files in a workspace.

    Args:
        workspace_id: The workspace identifier.
        pattern: Glob pattern to match files.
        max_depth: Maximum directory depth to traverse.

    Returns:
        List of relative file paths.
    """
    settings = get_workbench_settings()
    workspace_path = settings.get_workspace_path(workspace_id)

    if not workspace_path.exists():
        return []

    files = []
    for path in workspace_path.glob(pattern):
        if path.is_file():
            rel_path = path.relative_to(workspace_path)

            # Check depth
            if max_depth is not None:
                if len(rel_path.parts) > max_depth:
                    continue

            files.append(str(rel_path))

    return sorted(files)
