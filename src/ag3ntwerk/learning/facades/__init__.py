"""
Learning Facades - Domain-focused coordinators for the Learning Loops system.

Each facade owns a coherent set of subsystems and provides a focused API
for its domain. The main LearningOrchestrator delegates to these facades.
"""

from ag3ntwerk.learning.facades.core_learning import CoreLearningFacade
from ag3ntwerk.learning.facades.routing_facade import RoutingFacade
from ag3ntwerk.learning.facades.prediction_facade import PredictionFacade
from ag3ntwerk.learning.facades.experimentation_facade import ExperimentationFacade
from ag3ntwerk.learning.facades.proactive_facade import ProactiveFacade
from ag3ntwerk.learning.facades.autonomy_facade import AutonomyFacade
from ag3ntwerk.learning.facades.integration_facade import IntegrationFacade
from ag3ntwerk.learning.facades.evolution_facade import EvolutionFacade
from ag3ntwerk.learning.facades.intelligence_facade import IntelligenceFacade
from ag3ntwerk.learning.facades.autonomy_advanced_facade import AdvancedAutonomyFacade
from ag3ntwerk.learning.facades.metacognition_facade import MetacognitionFacade

__all__ = [
    "CoreLearningFacade",
    "RoutingFacade",
    "PredictionFacade",
    "ExperimentationFacade",
    "ProactiveFacade",
    "AutonomyFacade",
    "IntegrationFacade",
    "EvolutionFacade",
    "IntelligenceFacade",
    "AdvancedAutonomyFacade",
    "MetacognitionFacade",
]
