"""Imports all domain models so that Base.metadata is fully populated.

Import this module anywhere you need the complete metadata (e.g., alembic/env.py).
"""

from app.models.care_log import CareLog  # noqa: F401
from app.models.chat_request import ChatRequest  # noqa: F401
from app.models.environment_snapshot import EnvironmentSnapshot  # noqa: F401
from app.models.llm_run import LlmRun  # noqa: F401
from app.models.plant import Plant  # noqa: F401
from app.models.plant_character import PlantCharacter  # noqa: F401
from app.models.recommendation_evidence import RecommendationEvidence  # noqa: F401
from app.models.retrieved_chunk import RetrievedChunk  # noqa: F401
from app.models.sensor_reading import SensorReading  # noqa: F401
from app.models.species_profile import SpeciesProfile  # noqa: F401
from app.models.runtime_endpoint import RuntimeEndpoint  # noqa: F401
from app.models.sensor_metric_rollup import SensorMetricRollup  # noqa: F401
from app.models.plant_sensor_device import PlantSensorDevice  # noqa: F401
from app.models.user import User  # noqa: F401
