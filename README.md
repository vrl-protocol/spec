# Verifiable Reality Layer

Production-grade, deterministic U.S. import compliance engine with PostgreSQL-backed evidence storage, append-only audit chaining, and an autonomous 10-agent ZK Engineering Unit.

## ZK Engineering Unit

The repository includes a coordinated 10-agent engineering system with:
- ZK Architect Agent
- Circuit Engineer Agent
- Backend Integration Agent
- Verifier Agent
- Performance Optimization Agent
- Security Audit Agent
- Data Integrity Agent
- DevOps / Infrastructure Agent
- Testing & Simulation Agent
- Research Agent

The coordinator lives in `coordinator/system.py` and handles:
- task assignment
- parallel cycle execution
- persistent shared memory updates
- agent performance scoring
- replacement of underperforming agents

Shared memory lives in `memory/shared_memory.py` and stores:
- strategy memory
- circuit memory
- vulnerability memory
- performance memory

## Project structure

```text
verifiable-reality-layer/
  agents/
  coordinator/
  zk/
  backend/
  infra/
  app/
  api/
  core/
  memory/
  tests/
  scripts/
  docs/
```

## First-cycle execution

```powershell
python orchestrator.py
```

This executes the first engineering cycle, writes a cycle report to `logs/`, and updates shared memory under `memory/`.

## Validation

```powershell
python -m pytest -q
```
