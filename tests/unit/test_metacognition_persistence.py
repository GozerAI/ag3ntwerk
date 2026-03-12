"""Tests for metacognition auto-persistence (Phase 2, Step 6)."""

import json
import os
import tempfile
import pytest

from ag3ntwerk.modules.metacognition.service import MetacognitionService
from ag3ntwerk.core.personality import PersonalityProfile, PERSONALITY_SEEDS


class TestAutoSaveConfig:
    """Tests for auto-save configuration."""

    def test_default_profile_path_set(self):
        svc = MetacognitionService()
        assert svc._profile_path.endswith("profiles.json")
        assert "metacognition" in svc._profile_path

    def test_custom_profile_path(self, tmp_path):
        custom_path = str(tmp_path / "custom.json")
        svc = MetacognitionService(profile_path=custom_path)
        assert svc._profile_path == custom_path

    def test_auto_save_default_true(self):
        svc = MetacognitionService()
        assert svc._auto_save is True

    def test_auto_save_can_be_disabled(self):
        svc = MetacognitionService()
        svc._auto_save = False
        assert svc._auto_save is False


class TestLoadOnStartup:
    """Tests for load_on_startup()."""

    def test_load_on_startup_returns_zero_when_no_file(self, tmp_path):
        svc = MetacognitionService(profile_path=str(tmp_path / "nonexistent_profiles_xyz.json"))
        count = svc.load_on_startup()
        assert count == 0

    def test_load_on_startup_loads_saved_profiles(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            svc1 = MetacognitionService(profile_path=f.name)
            svc1.register_agent("Forge")
            svc1.register_agent("Echo")
            svc1.save_profiles(f.name)

            svc2 = MetacognitionService(profile_path=f.name)
            count = svc2.load_on_startup()
            assert count == 2
            assert svc2.is_registered("Forge")
            assert svc2.is_registered("Echo")

        os.unlink(f.name)

    def test_load_on_startup_preserves_evolved_traits(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            svc1 = MetacognitionService(profile_path=f.name)
            svc1.register_agent("Forge")

            # Force some evolution
            evolver = svc1._evolvers["Forge"]
            for _ in range(10):
                evolver.profile.risk_tolerance.sample_count += 1
            evolver.process_outcome(success=False, task_type="test", task_id="t1")

            original_risk = evolver.profile.risk_tolerance.value
            svc1.save_profiles(f.name)

            svc2 = MetacognitionService(profile_path=f.name)
            count = svc2.load_on_startup()
            assert count == 1
            loaded_risk = svc2.get_profile("Forge").risk_tolerance.value
            assert abs(loaded_risk - original_risk) < 1e-6

        os.unlink(f.name)


class TestSaveIfAuto:
    """Tests for save_if_auto()."""

    def test_save_if_auto_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "metacognition", "profiles.json")
            svc = MetacognitionService(profile_path=path)
            svc.register_agent("Forge")
            svc.save_if_auto()
            assert os.path.exists(path)

    def test_save_if_auto_skips_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "profiles.json")
            svc = MetacognitionService(profile_path=path)
            svc._auto_save = False
            svc.register_agent("Forge")
            svc.save_if_auto()
            assert not os.path.exists(path)

    def test_save_if_auto_handles_errors_gracefully(self):
        svc = MetacognitionService(profile_path="/nonexistent/deep/path/profiles.json")
        # Should not raise — just log warning
        svc.save_if_auto()

    def test_save_if_auto_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "profiles.json")
            svc1 = MetacognitionService(profile_path=path)
            svc1.register_agent("Forge")
            svc1.register_agent("Keystone")
            svc1.save_if_auto()

            svc2 = MetacognitionService(profile_path=path)
            count = svc2.load_on_startup()
            assert count == 2
            assert svc2.get_profile("Forge").agent_code == "Forge"
            assert svc2.get_profile("Keystone").agent_code == "Keystone"


class TestFacadeAutoSave:
    """Tests that the facade calls save_if_auto after phase."""

    def test_run_metacognition_phase_triggers_save(self):
        from ag3ntwerk.learning.facades.metacognition_facade import MetacognitionFacade

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "profiles.json")
            svc = MetacognitionService(profile_path=path)
            svc.register_agent("Forge")

            facade = MetacognitionFacade()
            facade.connect_service(svc)

            # Process an outcome (so buffer has data)
            facade.process_outcome_with_reflection(
                agent_code="Forge",
                task_id="t1",
                task_type="code_review",
                success=True,
            )

            # Run metacognition phase
            facade.run_metacognition_phase()

            # File should exist after auto-save
            assert os.path.exists(path)


class TestCoSLoadOnStartup:
    """Tests that Overwatch.connect_metacognition calls load_on_startup."""

    def test_connect_metacognition_loads_profiles(self):
        from ag3ntwerk.agents.overwatch.agent import Overwatch
        from ag3ntwerk.core.base import Agent, Task, TaskResult

        class SimpleAgent(Agent):
            def can_handle(self, task):
                return True

            async def execute(self, task):
                return TaskResult(task_id=task.id, success=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "profiles.json")

            # Pre-save profiles
            svc1 = MetacognitionService(profile_path=path)
            svc1.register_agent("Forge")
            svc1.save_profiles(path)

            # New service with same path — should load on connect
            svc2 = MetacognitionService(profile_path=path)
            cos = Overwatch()
            agent = SimpleAgent("Forge", "Forge", "tech")
            cos.register_subordinate(agent)

            cos.connect_metacognition(svc2)

            # Forge should have been loaded from file, not re-registered
            assert svc2.is_registered("Forge")
            assert agent.personality is not None
            assert agent.personality.agent_code == "Forge"
