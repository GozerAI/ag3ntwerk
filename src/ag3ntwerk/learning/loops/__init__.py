"""
Learning Loops - Level-specific learning implementations.

Each level in the agent hierarchy has its own learning loop that
focuses on the patterns most relevant to that level:

- ExecutiveLearningLoop: Cross-domain patterns, manager performance, routing
- ManagerLearningLoop: Specialist routing, error patterns, complexity
- SpecialistLearningLoop: Confidence calibration, skill refinement, recovery

Usage:
    ```python
    from ag3ntwerk.learning.loops import (
        LearningLoop,
        ExecutiveLearningLoop,
        ManagerLearningLoop,
        SpecialistLearningLoop,
    )

    # Create a specialist loop
    loop = SpecialistLearningLoop(
        specialist_code="SD",
        manager_code="AM",
        capabilities=["code_generation", "refactoring"],
        pattern_store=pattern_store,
        db=db,
    )

    # Analyze outcomes
    patterns = await loop.analyze_outcomes(outcomes)
    ```
"""

from ag3ntwerk.learning.loops.base import LearningLoop
from ag3ntwerk.learning.loops.agent_loop import ExecutiveLearningLoop
from ag3ntwerk.learning.loops.manager_loop import ManagerLearningLoop
from ag3ntwerk.learning.loops.specialist_loop import SpecialistLearningLoop

__all__ = [
    "LearningLoop",
    "ExecutiveLearningLoop",
    "ManagerLearningLoop",
    "SpecialistLearningLoop",
]
