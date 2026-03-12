"""
Tests for thread safety of the MetacognitionService.

The service uses a threading.Lock to protect shared mutable state
(trait snapshots, team outcomes, phase5 state). These tests verify
that concurrent access does not corrupt data, lose records, or deadlock.
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from ag3ntwerk.modules.metacognition.service import (
    MAX_TEAM_OUTCOMES,
    MAX_TRAIT_SNAPSHOTS,
    MetacognitionService,
    TeamOutcome,
    TraitSnapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_with_agents(*codes: str) -> MetacognitionService:
    """Create a service with auto-save disabled and pre-registered agents."""
    svc = MetacognitionService()
    svc._auto_save = False
    for code in codes:
        svc.register_agent(code)
    return svc


# ============================================================
# 1. Concurrent Trait Snapshots
# ============================================================


class TestConcurrentTraitSnapshots:
    """Thread safety of record_trait_snapshot()."""

    def test_concurrent_snapshots_no_data_loss(self):
        """Multiple threads calling record_trait_snapshot -- every call for a
        distinct agent should produce a snapshot without data loss."""
        agents = [f"AG{i}" for i in range(20)]
        svc = _make_service_with_agents(*agents)

        # Bypass the min-interval check by using unique agents per thread
        errors = []

        def record(agent_code):
            try:
                svc.record_trait_snapshot(agent_code)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(record, code) for code in agents]
            for f in as_completed(futures):
                f.result()

        assert errors == [], f"Errors during concurrent snapshots: {errors}"
        # Each unique agent should have exactly one snapshot
        assert len(svc.trait_snapshots) == len(agents)

    def test_concurrent_snapshots_respect_max_cap(self):
        """Even under heavy concurrent appending, the deque should never
        exceed MAX_TRAIT_SNAPSHOTS."""
        svc = _make_service_with_agents("Forge")
        # Pre-fill close to the cap
        for _ in range(MAX_TRAIT_SNAPSHOTS - 5):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5},
                    trait_baselines={"thoroughness": 0.5},
                    # Spread timestamps far apart so interval check passes
                    timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
                )
            )

        # Now hammer it with many more agents so each passes the interval check
        extra_agents = [f"X{i}" for i in range(50)]
        for code in extra_agents:
            svc.register_agent(code)

        def record(code):
            svc.record_trait_snapshot(code)

        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(record, extra_agents))

        # The underlying deque has maxlen=MAX_TRAIT_SNAPSHOTS
        assert len(svc._trait_snapshots) <= MAX_TRAIT_SNAPSHOTS

    def test_snapshot_ordering_preserved_under_contention(self):
        """Snapshots appended under contention maintain chronological order
        (timestamps are non-decreasing)."""
        agents = [f"ORD{i}" for i in range(30)]
        svc = _make_service_with_agents(*agents)

        def record(code):
            svc.record_trait_snapshot(code)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(record, agents))

        timestamps = [s.timestamp for s in svc._trait_snapshots]
        for i in range(1, len(timestamps)):
            assert (
                timestamps[i] >= timestamps[i - 1]
            ), f"Snapshot {i} timestamp {timestamps[i]} < previous {timestamps[i - 1]}"


# ============================================================
# 2. Concurrent Save / Load
# ============================================================


class TestConcurrentSaveLoad:
    """Thread safety of save_phase5_state / load_phase5_state."""

    def test_simultaneous_save_and_load(self, tmp_path):
        """Concurrent save and load should not corrupt the state file."""
        path = str(tmp_path / "phase5.json")
        svc = _make_service_with_agents("Forge", "Keystone")
        svc._trait_snapshots.append(
            TraitSnapshot(
                agent_code="Forge",
                trait_values={"thoroughness": 0.8},
                trait_baselines={"thoroughness": 0.7},
            )
        )
        # Initial save so load has something to read
        svc.save_phase5_state(path)

        errors = []

        def saver():
            try:
                for _ in range(20):
                    svc.save_phase5_state(path)
            except Exception as exc:
                errors.append(exc)

        def loader():
            try:
                for _ in range(20):
                    svc2 = MetacognitionService()
                    svc2._auto_save = False
                    # On Windows, concurrent file access can raise
                    # PermissionError; retry a few times.
                    for attempt in range(3):
                        try:
                            svc2.load_phase5_state(path)
                            break
                        except (PermissionError, OSError):
                            time.sleep(0.01)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=saver), threading.Thread(target=loader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Errors during concurrent save/load: {errors}"

        # File should still be valid JSON
        with open(path) as f:
            data = json.load(f)
        assert "trait_snapshots" in data

    def test_multiple_concurrent_saves_produce_valid_json(self, tmp_path):
        """Several threads saving simultaneously should always leave a valid
        JSON file on disk."""
        path = str(tmp_path / "phase5.json")
        svc = _make_service_with_agents("Forge")
        for i in range(10):
            svc._trait_snapshots.append(
                TraitSnapshot(
                    agent_code="Forge",
                    trait_values={"thoroughness": 0.5 + i * 0.01},
                    trait_baselines={"thoroughness": 0.5},
                    timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
                )
            )

        errors = []

        def save():
            try:
                for _ in range(15):
                    svc.save_phase5_state(path)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=save) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Errors during concurrent saves: {errors}"

        # Final file must be parseable
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data["trait_snapshots"], list)

    def test_load_during_active_recording(self, tmp_path):
        """Loading state while another thread is recording snapshots should
        not lose in-flight data from the recording thread."""
        path = str(tmp_path / "phase5.json")
        agents = [f"REC{i}" for i in range(10)]
        svc = _make_service_with_agents(*agents)
        svc.save_phase5_state(path)  # seed file

        record_count = threading.Event()
        errors = []

        def recorder():
            try:
                for code in agents:
                    svc.record_trait_snapshot(code)
                record_count.set()
            except Exception as exc:
                errors.append(exc)

        def loader():
            try:
                record_count.wait(timeout=10)
                svc2 = MetacognitionService()
                svc2._auto_save = False
                # Save first so we can load a consistent copy
                svc.save_phase5_state(path)
                svc2.load_phase5_state(path)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=recorder)
        t2 = threading.Thread(target=loader)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        assert errors == [], f"Errors: {errors}"
        # The recording thread added snapshots for all agents
        assert len(svc.trait_snapshots) == len(agents)


# ============================================================
# 3. Concurrent Team Outcomes
# ============================================================


class TestConcurrentTeamOutcomes:
    """Thread safety of record_team_outcome()."""

    def test_concurrent_team_outcome_recording(self):
        """Multiple threads recording team outcomes simultaneously should
        not lose any records."""
        svc = _make_service_with_agents("Forge", "Keystone", "Echo")
        n_per_thread = 50
        n_threads = 8

        errors = []

        def record_outcomes(thread_id):
            try:
                for i in range(n_per_thread):
                    svc.record_team_outcome(
                        team=["Forge", "Keystone"],
                        task_type=f"task_t{thread_id}",
                        success=(i % 2 == 0),
                        task_id=f"t{thread_id}_{i}",
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=record_outcomes, args=(tid,)) for tid in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Errors: {errors}"
        expected = n_per_thread * n_threads
        # deque maxlen may cap, but we should get min(expected, MAX_TEAM_OUTCOMES)
        assert len(svc.team_outcomes) == min(expected, MAX_TEAM_OUTCOMES)

    def test_team_outcome_count_within_bounds(self):
        """Even with massive concurrent writes the deque never exceeds its cap."""
        svc = _make_service_with_agents("Forge", "Keystone")
        n_per_thread = 200
        n_threads = 10

        def record_outcomes(thread_id):
            for i in range(n_per_thread):
                svc.record_team_outcome(
                    team=["Forge", "Keystone"],
                    task_type="stress",
                    success=True,
                    task_id=f"s{thread_id}_{i}",
                )

        threads = [
            threading.Thread(target=record_outcomes, args=(tid,)) for tid in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(svc._team_outcomes) <= MAX_TEAM_OUTCOMES


# ============================================================
# 4. Mixed Operations
# ============================================================


class TestMixedConcurrentOperations:
    """Simultaneous operations across different lock-protected methods."""

    def test_snapshot_save_and_team_outcome_simultaneously(self, tmp_path):
        """Three different operation types running concurrently should not
        interfere with each other."""
        path = str(tmp_path / "phase5.json")
        agents = [f"MIX{i}" for i in range(10)]
        svc = _make_service_with_agents(*agents)
        svc.save_phase5_state(path)

        errors = []
        barrier = threading.Barrier(3, timeout=10)

        def snapshotter():
            try:
                barrier.wait()
                for code in agents:
                    svc.record_trait_snapshot(code)
            except Exception as exc:
                errors.append(exc)

        def saver():
            try:
                barrier.wait()
                for _ in range(10):
                    svc.save_phase5_state(path)
            except Exception as exc:
                errors.append(exc)

        def team_recorder():
            try:
                barrier.wait()
                for i in range(50):
                    svc.record_team_outcome(
                        team=["MIX0", "MIX1"],
                        task_type="mixed",
                        success=(i % 3 != 0),
                        task_id=f"m{i}",
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=snapshotter),
            threading.Thread(target=saver),
            threading.Thread(target=team_recorder),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Errors during mixed operations: {errors}"
        # Snapshots were recorded
        assert len(svc.trait_snapshots) >= 1
        # Team outcomes were recorded
        assert len(svc.team_outcomes) >= 1
        # File is still valid
        with open(path) as f:
            data = json.load(f)
        assert "trait_snapshots" in data

    def test_high_frequency_operations_no_deadlock(self):
        """100+ rapid calls across all lock-protected methods should complete
        within a reasonable time without deadlocking."""
        agents = [f"HF{i}" for i in range(5)]
        svc = _make_service_with_agents(*agents)

        errors = []
        completed = threading.Event()

        def mixed_worker(worker_id):
            try:
                for i in range(100):
                    op = i % 3
                    if op == 0:
                        svc.record_trait_snapshot(agents[worker_id % len(agents)])
                    elif op == 1:
                        svc.record_team_outcome(
                            team=["HF0", "HF1"],
                            task_type="hf",
                            success=True,
                            task_id=f"hf_{worker_id}_{i}",
                        )
                    else:
                        # Read operations (no lock needed, but interleave them)
                        _ = svc.trait_snapshots
                        _ = svc.team_outcomes
            except Exception as exc:
                errors.append(exc)

        start = time.monotonic()
        threads = [threading.Thread(target=mixed_worker, args=(wid,)) for wid in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        elapsed = time.monotonic() - start

        assert errors == [], f"Errors during high-frequency ops: {errors}"
        # Should finish well within 30 seconds (no deadlock)
        assert elapsed < 30, f"Operations took {elapsed:.1f}s -- possible deadlock"
