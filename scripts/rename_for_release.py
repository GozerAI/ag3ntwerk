#!/usr/bin/env python3
"""
Bulk rename script for ag3ntwerk → ag3ntwerk public release.

Performs all text replacements in strict order (longest first)
to prevent substring corruption. Uses regex word-boundary matching
for agent code replacements.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories to exclude from processing
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Subprojects to exclude (they have their own release cycle)
EXCLUDE_PATHS = {
    ROOT / "src" / "nexus",
    ROOT / "src" / "sentinel",
}

# File patterns to process
INCLUDE_EXTENSIONS = {
    ".py", ".yaml", ".yml", ".toml", ".ini", ".md",
    ".sh", ".bat", ".cfg", ".txt", ".env", ".example",
    ".json", ".html", ".css", ".js",
}

INCLUDE_FILENAMES = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "Makefile", "Procfile",
}

# =============================================================
# REPLACEMENT RULES (applied in order)
# =============================================================

def build_replacements():
    """Build ordered list of (pattern, replacement) tuples."""
    rules = []

    # --- A. Package imports ---
    rules.append((r'\bfrom ag3ntwerk\.', 'from ag3ntwerk.'))
    rules.append((r'\bfrom ag3ntwerk\b', 'from ag3ntwerk'))
    rules.append((r'\bimport ag3ntwerk\.', 'import ag3ntwerk.'))
    rules.append((r'\bimport ag3ntwerk\b', 'import ag3ntwerk'))

    # --- B. Agent directory paths in imports (longest first) ---
    # 5-char agent codes in path context
    rules.append((r'\bagents\.cseco\b', 'agents.citadel'))
    rules.append((r'\bagents\.crevo\b', 'agents.vector'))
    rules.append((r'\bagents\.cengo\b', 'agents.foundry'))
    rules.append((r'\bagents\.ccomo\b', 'agents.accord'))
    # 4-char
    rules.append((r'\bagents\.crio\b', 'agents.aegis'))
    # 3-char
    rules.append((r'\bagents\.cos\b', 'agents.overwatch'))
    rules.append((r'\bagents\.coo\b', 'agents.nexus'))
    rules.append((r'\bagents\.cto\b', 'agents.forge'))
    rules.append((r'\bagents\.cfo\b', 'agents.keystone'))
    rules.append((r'\bagents\.cmo\b', 'agents.echo'))
    rules.append((r'\bagents\.cio\b', 'agents.sentinel'))
    rules.append((r'\bagents\.cpo\b', 'agents.blueprint'))
    rules.append((r'\bagents\.cro\b', 'agents.axiom'))
    rules.append((r'\bagents\.cdo\b', 'agents.index_agent'))
    rules.append((r'\bagents\.cso\b', 'agents.compass'))
    rules.append((r'\bagents\.cco\b', 'agents.beacon'))

    # --- C. Base class renames ---
    rules.append((r'\bCSuiteAgent\b', 'Agent'))
    rules.append((r'\bCSuiteError\b', 'AgentWerkError'))
    rules.append((r'\bCSuiteMCPServer\b', 'AgentWerkMCPServer'))
    rules.append((r'\bCSuiteManager\b', 'AgentWerkManager'))

    # --- D. Agent code string literals → codenames (word-boundary, longest first) ---
    # Module handler classes first (most specific) — E merged here for ordering
    rules.append((r'\bCSecOModuleHandler\b', 'CitadelModuleHandler'))
    rules.append((r'\bCRevOModuleHandler\b', 'VectorModuleHandler'))
    rules.append((r'\bCEngOModuleHandler\b', 'FoundryModuleHandler'))
    rules.append((r'\bCComOModuleHandler\b', 'AccordModuleHandler'))
    rules.append((r'\bCRiOModuleHandler\b', 'AegisModuleHandler'))
    rules.append((r'\bCoSModuleHandler\b', 'OverwatchModuleHandler'))
    rules.append((r'\bCOOModuleHandler\b', 'NexusModuleHandler'))
    rules.append((r'\bCTOModuleHandler\b', 'ForgeModuleHandler'))
    rules.append((r'\bCFOModuleHandler\b', 'KeystoneModuleHandler'))
    rules.append((r'\bCMOModuleHandler\b', 'EchoModuleHandler'))
    rules.append((r'\bCIOModuleHandler\b', 'SentinelModuleHandler'))
    rules.append((r'\bCPOModuleHandler\b', 'BlueprintModuleHandler'))
    rules.append((r'\bCROModuleHandler\b', 'AxiomModuleHandler'))
    rules.append((r'\bCDOModuleHandler\b', 'IndexModuleHandler'))
    rules.append((r'\bCSOModuleHandler\b', 'CompassModuleHandler'))
    rules.append((r'\bCCOModuleHandler\b', 'BeaconModuleHandler'))

    # 5-char agent codes
    rules.append((r'\bCSecO\b', 'Citadel'))
    rules.append((r'\bCRevO\b', 'Vector'))
    rules.append((r'\bCEngO\b', 'Foundry'))
    rules.append((r'\bCComO\b', 'Accord'))
    # 4-char
    rules.append((r'\bCRiO\b', 'Aegis'))
    # 3-char agent codes
    rules.append((r'\bCoS\b', 'Overwatch'))
    rules.append((r'\bCOO\b', 'Nexus'))
    rules.append((r'\bCTO\b', 'Forge'))
    rules.append((r'\bCFO\b', 'Keystone'))
    rules.append((r'\bCMO\b', 'Echo'))
    rules.append((r'\bCIO\b', 'Sentinel'))
    rules.append((r'\bCPO\b', 'Blueprint'))
    rules.append((r'\bCRO\b', 'Axiom'))
    rules.append((r'\bCDO\b', 'Index'))
    rules.append((r'\bCSO\b', 'Compass'))
    rules.append((r'\bCCO\b', 'Beacon'))

    # --- F. Environment variables ---
    rules.append((r'\bCSUITE_', 'AGENTWERK_'))

    # --- G. Redis/domain model names ---
    rules.append((r'\bcsuite:', 'ag3ntwerk:'))
    rules.append((r'\bcsuite-technical\b', 'ag3ntwerk-technical'))
    rules.append((r'\bcsuite-business\b', 'ag3ntwerk-business'))
    rules.append((r'\bcsuite-operations\b', 'ag3ntwerk-operations'))
    rules.append((r'\bcsuite-governance\b', 'ag3ntwerk-governance'))
    rules.append((r'\bcsuite-strategy\b', 'ag3ntwerk-strategy'))

    # --- H. MCP tool names ---
    rules.append((r'\bcsuite_list_agents\b', 'ag3ntwerk_list_agents'))
    rules.append((r'\bcsuite_get_agent\b', 'ag3ntwerk_get_agent'))
    rules.append((r'\bcsuite_delegate\b', 'ag3ntwerk_delegate'))
    rules.append((r'\bcsuite_status\b', 'ag3ntwerk_status'))

    # --- I. Prose/branding ---
    rules.append((r'\bC-Suite\b', 'ag3ntwerk'))
    rules.append((r'\bc-suite\b', 'ag3ntwerk'))
    rules.append((r'"ag3ntwerk"', '"ag3ntwerk"'))
    rules.append((r"'ag3ntwerk'", "'ag3ntwerk'"))
    rules.append((r'\bcsuite\b', 'ag3ntwerk'))

    # --- J. STANDARD_AGENTS → STANDARD_AGENTS ---
    rules.append((r'\bSTANDARD_EXECUTIVES\b', 'STANDARD_AGENTS'))
    rules.append((r'\bexecutive\b', 'agent'))
    rules.append((r'\bExecutive\b', 'Agent'))
    rules.append((r'\bEXECUTIVE\b', 'AGENT'))
    rules.append((r'\bexecutives\b', 'agents'))
    rules.append((r'\bExecutives\b', 'Agents'))
    rules.append((r'\bEXECUTIVES\b', 'AGENTS'))

    # --- K. Chief X Officer titles → codenames in strings/comments ---
    rules.append((r'Forge', 'Forge'))
    rules.append((r'Keystone', 'Keystone'))
    rules.append((r'Echo', 'Echo'))
    rules.append((r'Sentinel', 'Sentinel'))
    rules.append((r'Blueprint', 'Blueprint'))
    rules.append((r'Axiom', 'Axiom'))
    rules.append((r'Index', 'Index'))
    rules.append((r'Foundry', 'Foundry'))
    rules.append((r'Citadel', 'Citadel'))
    rules.append((r'Beacon', 'Beacon'))
    rules.append((r'Vector', 'Vector'))
    rules.append((r'Aegis', 'Aegis'))
    rules.append((r'Accord', 'Accord'))
    rules.append((r'Compass', 'Compass'))
    rules.append((r'Nexus', 'Nexus'))
    rules.append((r'Overwatch', 'Overwatch'))

    return rules


def should_process(filepath: Path) -> bool:
    """Check if a file should be processed."""
    # Check exclusion paths
    for excl in EXCLUDE_PATHS:
        try:
            filepath.relative_to(excl)
            return False
        except ValueError:
            pass

    # Check exclusion dirs
    for part in filepath.parts:
        if part in EXCLUDE_DIRS:
            return False

    # Check file extension or name
    if filepath.name in INCLUDE_FILENAMES:
        return True
    if filepath.suffix in INCLUDE_EXTENSIONS:
        return True

    return False


def process_file(filepath: Path, rules: list, dry_run: bool = False) -> int:
    """Process a single file with all replacement rules. Returns count of changes."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return 0

    original = content
    total_changes = 0

    for pattern, replacement in rules:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            # Count replacements
            changes = len(re.findall(pattern, content))
            total_changes += changes
            content = new_content

    if content != original and not dry_run:
        filepath.write_text(content, encoding="utf-8")

    return total_changes


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    rules = build_replacements()
    compiled_rules = [(re.compile(p), r) for p, r in rules]

    total_files = 0
    total_changes = 0
    changed_files = 0

    for filepath in sorted(ROOT.rglob("*")):
        if not filepath.is_file():
            continue
        if not should_process(filepath):
            continue

        total_files += 1
        changes = process_file(filepath, compiled_rules, dry_run)

        if changes > 0:
            changed_files += 1
            total_changes += changes
            if verbose:
                rel = filepath.relative_to(ROOT)
                print(f"  {rel}: {changes} replacements")

    action = "Would change" if dry_run else "Changed"
    print(f"\n{action} {changed_files} files ({total_changes} replacements) out of {total_files} files scanned.")

    if dry_run:
        print("(Dry run — no files were modified)")


if __name__ == "__main__":
    main()
