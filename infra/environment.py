from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build_environment_manifest() -> dict:
    return {
        'root': str(ROOT),
        'execution_mode': 'local_or_vm_ready',
        'shared_repository': True,
        'folders': {
            'agents': 'agent specializations and foundations',
            'coordinator': 'task assignment, performance tracking, agent lifecycle',
            'zk': 'architecture, circuits, provers, verifiers',
            'backend': 'trace extraction and proof integration pipeline',
            'infra': 'environment topology and deployment manifests',
            'tests': 'system, determinism, and hardening validation',
            'memory': 'persistent shared memory and performance history',
        },
        'services': ['coordinator.loop', 'agent.workers', 'shared_memory', 'deterministic_engine', 'zk_stub_pipeline'],
    }
