from __future__ import annotations

import json

from coordinator.system import ZKCoordinator


def run_system(cycles: int = 3) -> dict:
    coordinator = ZKCoordinator()
    executions = [coordinator.run_cycle(cycle) for cycle in range(1, cycles + 1)]
    summary = {
        'cycles': cycles,
        'results_per_cycle': [len(execution.results) for execution in executions],
        'blocked_tasks_per_cycle': [len(execution.blocked_tasks) for execution in executions],
        'artifact_nodes_per_cycle': [execution.artifact_graph['node_count'] for execution in executions],
        'artifact_edges_per_cycle': [execution.artifact_graph['edge_count'] for execution in executions],
        'log_paths': [execution.log_path for execution in executions],
        'final_memory_summary': executions[-1].memory_summary if executions else {},
        'final_performance': executions[-1].performance if executions else {},
    }
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == '__main__':
    run_system()
