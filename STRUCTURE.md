# Repository Structure

This document describes the top-level folders in the Verifiable Reality Layer project. Each folder has a specific role in the ZK proof system engineering and AI output verification pipeline.

## agents/

The 10-agent ZK Engineering Unit. Each subdirectory contains an implementation of `BaseAgent` that handles a specific domain: `zk_architect`, `circuit_engineer`, `backend_integration`, `verifier`, `security_audit`, `testing_simulation`, `performance_optimizer`, `data_integrity`, `devops`, and `research`. Agents are stateless and dispatched by the Coordinator; results update SharedMemory. All agents follow the deterministic task-result contract defined in `agents/base.py`.

## coordinator/

Orchestrates the multi-agent workflow. `ZKCoordinator` dispatches tasks to agents, tracks performance via `PerformanceTracker`, manages artifact dependencies with `ArtifactGraph`, and logs cycle execution summaries. The coordinator maintains determinism by ensuring all agent runs are reproducible given the same task and memory snapshot.

## memory/

Shared state repository for the agent system. `SharedMemory` stores strategy entries (learned patterns per domain), circuit records (constraint counts and proving times), and vulnerability findings. This enables agents to access prior discoveries without reimplementing computations. Memory is persisted and can be checkpointed.

## core/

Core verification logic and audit chain infrastructure. Contains the deterministic audit trail, constraint tracking, and evidence collection for proof bundles. Provides the `AUDIT_CHAIN_PARTITIONS` that structure verification evidence across domains.

## zk/

Zero-knowledge proof system architecture and interfaces. Defines `ArtifactType`, `DeterministicArtifact`, and the proving system blueprint. Contains architecture selection logic (Groth16, Plonk, STARK), circuit sizing guidelines, and migration paths for proof system transitions.

## infra/

Infrastructure and deployment. Includes Docker configurations, CI/CD pipeline definitions, and environment manifest building. Provides runtime configuration and deployment orchestration for the VRL system.

## sdk/

Software Development Kits for integration. Contains language-specific implementations:
- **python/**: Python SDK with proof bundle construction and verification utilities; ready for PyPI publishing
- **go/**: Go SDK for high-performance proof operations
- **typescript/**: TypeScript/Node.js SDK for browser and server-side JavaScript environments

## verifier/

Standalone proof bundle verifier. `vrl_verify.py` is a zero-dependency command-line tool that implements the 10-step VRL verification procedure (Spec §12) with color-coded output, verbose mode, and proper exit codes. Works offline with only Python stdlib.

## registry/

Proof circuit registry and schema. Documents circuit specifications, provides a registry of approved circuits and their constraints, includes JSON schema for bundle validation, and tooling for registry maintenance and querying.

## docs/

GitHub Pages documentation site. Generated HTML documentation including the VRL specification, verification guides, audit checklists, trust model, TLS setup, and security audit reports. Provides the public-facing reference for the protocol.

## ui/

Web-based user interface. Interactive dashboard (`index.html`) for exploring proof bundles, verifying registrations, and visualizing the audit chain. Provides a visual interface complementing the CLI tools.

## api/

REST API server. FastAPI application (`main.py`, `routes.py`) that exposes proof bundle operations, verification endpoints, and registration queries. Integrates with the backend and app services.

## backend/

Proof generation and data pipeline. Handles ZK circuit compilation, proof generation (`zk_pipeline.py`), proof queue management, and verified dataset export. Bridges the agent system with actual cryptographic proving.

## tests/

Comprehensive test suite covering determinism, concurrency, database persistence, security hardening, hypothesis-based fuzzing, and production guardrails. Tests ensure reproducibility and correctness of both the agent system and proof verification.

## app/

Application layer with database and service integration. Houses database connection pooling, repository patterns for proof storage, and service implementations for evidence management and training data workflows.

## Additional Directories

- **security/**: Security policies and constraint definitions for the proof system
- **models/**: Data models for proofs, bundles, and audit records
- **scripts/**: Utility scripts for batch operations and migrations
- **proposals/**: Enhancement proposals and RFCs
- **migrations/**: Database schema migrations and upgrade scripts
- **utils/**: Helper functions and common utilities
- **logs/**: Runtime logs and cycle execution records
