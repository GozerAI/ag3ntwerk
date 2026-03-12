# ag3ntwerk Agent Architecture

## Overview

This document maps the 15 ag3ntwerk agents (plus 1 deprecated alias) to their deployment architecture within the `src/ag3ntwerk/agents/` package. All agents are **implemented** and follow a uniform agent hierarchy pattern.

## Architecture: Unified Agent Package

All agents live under `src/ag3ntwerk/agents/{code}/`, each containing their own agent, managers, specialists, and models. They are organized into functional **stacks** for logical grouping. External services (Nexus) are accessed via bridges.

### Stack 1: Operations Stack

Governed by Overwatch (Overwatch) as the internal coordinator/orchestrator. Handles day-to-day execution, finance, data, risk, compliance, and information governance.

| Code | Title | Codename | Directory | Status | Core Function |
|------|-------|----------|-----------|--------|---------------|
| Overwatch | Overwatch | **Overwatch** | `cos/` | Implemented | Coordinate all agents; turn strategy into execution |
| Keystone | Keystone | **Keystone** | `cfo/` | Implemented | Protect and grow financial health; allocate resources |
| Index | Index | **Index** | `cdo/` | Implemented | Make data usable, trustworthy, and leverageable (absorbed CKO) |
| Aegis | Aegis | **Aegis** | `crio/` | Implemented | Anticipate and mitigate threats to objectives |
| Accord | Accord | **Accord** | `ccomo/` | Implemented | Keep business within legal/regulatory/ethical bounds |
| Sentinel | Sentinel | **Sentinel** | `cio/` | Implemented | Govern information, systems-of-record, decision integrity |

> **Nexus (Nexus)**: The `coo/` directory is a **deprecated compatibility shim** that re-exports Overwatch. Nexus is now an external strategic service accessed via `bridges/nexus_bridge.py`. See [Nexus Deprecation](#coo-deprecation) below.

### Stack 2: Technology Stack

Builds and maintains the technical foundation.

| Code | Title | Codename | Directory | Status | Core Function |
|------|-------|----------|-----------|--------|---------------|
| Forge | Forge | **Forge** | `cto/` | Implemented | Build and evolve the technical foundation |
| Foundry | Foundry | **Foundry** | `cengo/` | Implemented | Deliver working systems on time with quality |
| Citadel | Citadel | **Citadel** | `cseco/` | Implemented | Protect systems, identities, data, and operations |

### Stack 3: Revenue Stack

Owns revenue generation, customer operations, and market presence.

| Code | Title | Codename | Directory | Status | Core Function |
|------|-------|----------|-----------|--------|---------------|
| Vector | Vector | **Vector** | `crevo/` | Implemented | Own revenue outcomes: acquisition, expansion, retention |
| Beacon | Beacon | **Beacon** | `cco/` | Implemented | Own customer relationships, satisfaction, and advocacy |
| Echo | Echo | **Echo** | `cmo/` | Implemented | Create demand, brand trust, and market pull |

### Stack 4: Product Stack

Drives product development and customer value maximization.

| Code | Title | Codename | Directory | Status | Core Function |
|------|-------|----------|-----------|--------|---------------|
| Blueprint | Blueprint | **Blueprint** | `cpo/` | Implemented | Decide what to build and why; maximize customer value |

### Stack 5: Strategy & Research Stack

Sets direction and generates validated insights.

| Code | Title | Codename | Directory | Status | Core Function |
|------|-------|----------|-----------|--------|---------------|
| Compass | Compass | **Compass** | `cso/` | Implemented | Set direction, make tradeoffs, maintain strategic coherence |
| Axiom | Axiom | **Axiom** | `cro/` | Implemented | Turn unknowns into knowns; produce validated insights |

## Module Structure

Every agent directory follows a consistent layout:

```
src/ag3ntwerk/agents/{code}/
    __init__.py          # Public API, exports
    agent.py             # Agent agent (C-level)
    managers.py          # Manager-level agents
    specialists.py       # Specialist-level agents
    models.py            # Enums, dataclasses, domain models
```

The agent hierarchy within each module:

```
Agent Agent (C-level)
├── Manager 1
│   ├── Specialist A
│   ├── Specialist B
│   └── Specialist C
├── Manager 2
│   ├── Specialist D
│   └── Specialist E
└── Manager 3
    └── Specialist F
```

Example (Forge/Forge):
```
src/ag3ntwerk/agents/forge/
    agent.py             # ForgeAgent (Forge Agent)
    managers.py          # ArchitectAgent, BuilderAgent, ValidatorAgent, ...
    specialists.py       # Sub-specialists for each manager
    models.py            # Technology domain models
```

## Bridges (External Service Connections)

External services are accessed via bridge modules in `src/ag3ntwerk/agents/bridges/`:

```
src/ag3ntwerk/agents/bridges/
    __init__.py
    nexus_bridge.py      # Connection to Nexus (external strategic brain)
    forge_bridge.py      # Forge integration bridge
    sentinel_bridge.py   # Sentinel integration bridge
```

## Nexus Deprecation

The Nexus role has been restructured:

- **Overwatch (Overwatch)** is the internal coordinator that orchestrates all agents day-to-day. This is the role formerly occupied by "Nexus" in earlier versions.
- **Nexus** is now an external strategic service (the "strategic brain") that provides high-level guidance to Overwatch via `bridges/nexus_bridge.py`.
- The `src/ag3ntwerk/agents/nexus/` directory contains only an `__init__.py` that re-exports Overwatch for backward compatibility. It issues a `DeprecationWarning` on import.

```python
# Old (deprecated):
from ag3ntwerk.agents.nexus import Nexus

# New (recommended):
from ag3ntwerk.agents.overwatch import Overwatch
```

## CKO Merger

The CKO (Chief Knowledge Officer) was merged into Index (Index). All knowledge management capabilities now live in `src/ag3ntwerk/agents/index_agent/`. There is no separate CKO directory.

## File Structure

```
F:\Projects\ag3ntwerk\
└── src\
    └── ag3ntwerk\
        └── agents\
            │
            │  ══════════════════════════════════════════════
            │  OPERATIONS STACK
            │  ══════════════════════════════════════════════
            ├── cos\                     # Overwatch (Overwatch) - Internal Coordinator
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   ├── models.py
            │   └── routing_rules.py
            │
            ├── coo\                     # Nexus (deprecated alias -> Overwatch)
            │   └── __init__.py          # Re-exports from cos/
            │
            ├── cfo\                     # Keystone (Keystone) - Financial Operations
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cdo\                     # Index (Index) - Data Governance
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── crio\                    # Aegis (Aegis) - Risk Management
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── ccomo\                   # Accord (Accord) - Compliance
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cio\                     # Sentinel (Sentinel) - Information Governance
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            │  ══════════════════════════════════════════════
            │  TECHNOLOGY STACK
            │  ══════════════════════════════════════════════
            ├── cto\                     # Forge (Forge) - Technical Foundation
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cengo\                   # Foundry (Foundry) - Engineering Execution
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cseco\                   # Citadel (Citadel) - Security Operations
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   ├── models.py
            │   └── bridge.py
            │
            │  ══════════════════════════════════════════════
            │  REVENUE STACK
            │  ══════════════════════════════════════════════
            ├── crevo\                   # Vector (Vector) - Revenue Operations
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cco\                     # Beacon (Beacon) - Customer Operations
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cmo\                     # Echo (Echo) - Marketing
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            │  ══════════════════════════════════════════════
            │  PRODUCT STACK
            │  ══════════════════════════════════════════════
            ├── cpo\                     # Blueprint (Blueprint) - Product Management
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            │  ══════════════════════════════════════════════
            │  STRATEGY & RESEARCH STACK
            │  ══════════════════════════════════════════════
            ├── cso\                     # Compass (Compass) - Strategy
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            ├── cro\                     # Axiom (Axiom) - Research
            │   ├── __init__.py
            │   ├── agent.py
            │   ├── managers.py
            │   ├── specialists.py
            │   └── models.py
            │
            │  ══════════════════════════════════════════════
            │  SHARED INFRASTRUCTURE
            │  ══════════════════════════════════════════════
            ├── bridges\                 # External service bridges
            │   ├── __init__.py
            │   ├── nexus_bridge.py      # Nexus (external strategic brain)
            │   ├── forge_bridge.py
            │   └── sentinel_bridge.py
            │
            ├── __init__.py              # Package init, agent registry
            └── base_handlers.py         # Shared base handler classes
```

## Dependency Graph

```
                    ┌────────────────────────────────────────────┐
                    │         OVERWATCH (Overwatch)                    │
                    │     Internal Coordinator                   │
                    │         ┌──────────────┐                   │
                    │         │ NexusBridge   │◄── Nexus         │
                    │         │ (external)    │    (Strategic     │
                    │         └──────────────┘     Brain)        │
                    └──────────────────┬─────────────────────────┘
                                       │
       ┌───────────────┬───────────────┼───────────────┬───────────────┐
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  OPERATIONS   │ │  TECHNOLOGY   │ │    REVENUE    │ │    PRODUCT    │ │   STRATEGY    │
│    STACK      │ │    STACK      │ │    STACK      │ │    STACK      │ │    STACK      │
├───────────────┤ ├───────────────┤ ├───────────────┤ ├───────────────┤ ├───────────────┤
│ Keystone(Keystone) │ │  Forge (Forge)  │ │ Vector(Vector) │ │Blueprint(Blueprint) │ │ Compass (Compass) │
│ Index (Index)   │ │ Foundry(Foundry)│ │ Beacon (Beacon)  │ │               │ │ Axiom (Axiom)   │
│ Aegis (Aegis)  │ │ Citadel(Citadel)│ │ Echo  (Echo)   │ │               │ │               │
│ Accord(Accord) │ │               │ │               │ │               │ │               │
│Sentinel(Sentinel)  │ │               │ │               │ │               │ │               │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
```

## Implementation Status

All phases are complete. Every agent is implemented with the full agent/managers/specialists/models hierarchy.

### Phase 1: Core Infrastructure -- Complete
- [x] Overwatch/Overwatch - Internal coordinator (formerly Nexus role)
- [x] Forge/Forge - Technical foundation
- [x] Sentinel/Sentinel - Information governance

### Phase 2: Operations Stack -- Complete
- [x] Keystone/Keystone - Financial operations
- [x] Index/Index - Data governance (absorbed CKO)
- [x] Aegis/Aegis - Risk management
- [x] Accord/Accord - Compliance

### Phase 3: Technology Stack -- Complete
- [x] Foundry/Foundry - Engineering execution
- [x] Citadel/Citadel - Security operations

### Phase 4: Strategy Stack -- Complete
- [x] Compass/Compass - Strategy
- [x] Axiom/Axiom - Research

### Phase 5: Revenue Stack -- Complete
- [x] Vector/Vector - Revenue operations
- [x] Beacon/Beacon - Customer operations
- [x] Echo/Echo - Marketing

### Phase 6: Product Stack -- Complete
- [x] Blueprint/Blueprint - Product management

## Codename Registry

| Codename | Agent | Stack | Directory |
|----------|-----------|-------|-----------|
| **Overwatch** | Overwatch | Operations | `cos/` |
| **Keystone** | Keystone | Operations | `cfo/` |
| **Index** | Index | Operations | `cdo/` |
| **Aegis** | Aegis | Operations | `crio/` |
| **Accord** | Accord | Operations | `ccomo/` |
| **Sentinel** | Sentinel | Operations | `cio/` |
| **Forge** | Forge | Technology | `cto/` |
| **Foundry** | Foundry | Technology | `cengo/` |
| **Citadel** | Citadel | Technology | `cseco/` |
| **Vector** | Vector | Revenue | `crevo/` |
| **Beacon** | Beacon | Revenue | `cco/` |
| **Echo** | Echo | Revenue | `cmo/` |
| **Blueprint** | Blueprint | Product | `cpo/` |
| **Compass** | Compass | Strategy | `cso/` |
| **Axiom** | Axiom | Strategy | `cro/` |

## Notes

1. **CKO Merger**: The CKO (Chief Knowledge Officer) capabilities were absorbed into Index/Index. Both handled making data/knowledge usable and accessible, so they were consolidated.

2. **Nexus/Nexus Split**: The original Nexus (Nexus) was split into two concerns: Overwatch (Overwatch) handles internal coordination and orchestration, while Nexus became an external strategic service accessed via bridges. The `coo/` module remains as a deprecated shim.

3. **Removed Agents**: Three agents from early planning were never implemented and have been dropped from the architecture:
   - CSalO (Rally) - Chief Sales Officer
   - CINO (Catalyst) - Chief Innovation Officer
   - CINVO (Venture) - Chief Investment Officer

4. **Inter-Stack Communication**: All modules communicate through the Overwatch (Overwatch) coordinator or via the distributed communicator for direct peer messaging. External strategic guidance flows from Nexus through the NexusBridge.

5. **Bridges**: The `bridges/` directory contains integration modules for external services (Nexus, Forge, Sentinel) that allow the internal agent network to interface with services running outside the agent package.
