# Commercial Licensing — ag3ntwerk

This project is dual-licensed:

- **AGPL-3.0** — Free for open-source use with copyleft obligations
- **Commercial License** — Proprietary use without AGPL requirements

## Tiers

| Feature | Community (Free) | Pro ($149/mo) | Enterprise ($499/mo) |
|---------|:---:|:---:|:---:|
| Base agent framework & routing | Yes | Yes | Yes |
| Learning Pipeline (9 phases) | — | Yes | Yes |
| 11 Learning Facades | — | Yes | Yes |
| Self-Architect, Meta-Learner | — | Yes | Yes |
| Cascade Predictor | — | Yes | Yes |
| VLS Pipeline + Evidence Gates | — | — | Yes |
| Advanced Metacognition | — | — | Yes |
| Fleet Orchestration | — | — | Yes |
| Swarm Bridge | — | — | Yes |
| Agent seats | Unlimited | 5 | Unlimited |
| Operations/month | — | 100K | 1M |
| Support SLA | Community | 48h email | 4h priority |

## How It Works

- **No license key** — All code runs (AGPL mode). Source is visible per AGPL obligations.
- **License key set** — Only entitled features are unlocked. Blocked features show a clear error with upgrade instructions.
- **Server unreachable** — Fail-closed for gated features.

## Getting a License

Visit **https://gozerai.com/pricing** or contact sales@gozerai.com.

```bash
export VINZY_LICENSE_KEY="your-key-here"
export VINZY_SERVER="https://api.gozerai.com"
```

## Feature Flags

Flags follow the convention `agw.{module}.{capability}`:

| Flag | Tier | Description |
|------|------|-------------|
| `agw.learning.pipeline` | Pro | 9-phase continuous learning |
| `agw.learning.facades` | Pro | 11 domain facades |
| `agw.learning.self_architect` | Pro | Self-architecture proposals |
| `agw.learning.meta_learner` | Pro | Parameter self-tuning |
| `agw.learning.cascade_predictor` | Pro | Downstream effect prediction |
| `agw.vls.pipeline` | Enterprise | Vertical Launch System |
| `agw.vls.evidence` | Enterprise | Evidence gate framework |
| `agw.vls.workflows` | Enterprise | VLS workflow orchestration |
| `agw.metacognition.advanced` | Enterprise | Personality evolution |
| `agw.distributed.fleet` | Enterprise | Fleet orchestration |
| `agw.swarm_bridge` | Enterprise | Swarm API bridge |

## Platform Bundle

All 5 products together: **$499/mo** (Pro) or **$1,999/mo** (Enterprise). Annual pricing available.
