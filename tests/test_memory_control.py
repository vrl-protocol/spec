from __future__ import annotations

from memory.shared_memory import SharedMemory


def test_memory_blocks_latest_failed_strategy(tmp_path):
    memory = SharedMemory(tmp_path)
    memory.record_strategy(
        domain='security',
        outcome='failure',
        pattern='continuous_adversarial_checks',
        detail='failed once',
        cycle=1,
        agent_id='security_audit',
    )
    decision = memory.control_decision(domain='security', pattern='continuous_adversarial_checks')
    assert decision['blocked'] is True


def test_memory_biases_to_successful_patterns(tmp_path):
    memory = SharedMemory(tmp_path)
    memory.record_strategy(
        domain='verification',
        outcome='success',
        pattern='structured_stub_verifier',
        detail='worked',
        cycle=1,
        agent_id='verifier_agent',
    )
    memory.record_strategy(
        domain='verification',
        outcome='success',
        pattern='structured_stub_verifier',
        detail='worked again',
        cycle=2,
        agent_id='verifier_agent',
    )
    assert memory.preferred_patterns('verification') == ['structured_stub_verifier']
