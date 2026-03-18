"""
Configuration for the extraction review application.

Configuration is loaded from configs/config.json via ResourceConfig.
The unified config contains both extraction settings and the JSON schema.

Extraction can run in two modes, controlled by the "extraction_agent_id" field
in configs/config.json:

  - Local (default): extraction_agent_id is null. Uses the json_schema and
    settings defined in config.json directly via extraction.run().

  - Remote agent: extraction_agent_id is set to a LlamaCloud extraction agent
    ID. Uses extraction.jobs.extract(extraction_agent_id=...) which delegates
    schema and settings to the remote agent. The local json_schema and settings
    in config.json are ignored — both extraction and the metadata workflow fetch
    the schema directly from the remote agent.
"""

import logging
from typing import Any, Literal

from pydantic import BaseModel

from .json_util import get_extraction_schema as get_extraction_schema

logger = logging.getLogger(__name__)


# The name of the collection to use for storing extracted data.
EXTRACTED_DATA_COLLECTION: str = "extraction-review"


class ExtractSettings(BaseModel):
    extraction_mode: Literal["FAST", "PREMIUM", "MULTIMODAL"]
    system_prompt: str | None = None
    citation_bbox: bool = False
    use_reasoning: bool = False
    cite_sources: bool = False
    confidence_scores: bool = False


class ExtractConfig(BaseModel):
    json_schema: dict[str, Any]
    settings: ExtractSettings
    # Set this to a LlamaCloud extraction agent ID to use a remote agent's
    # schema and settings instead of the local json_schema/settings above.
    # When set, extraction uses extraction.jobs.extract(extraction_agent_id=...)
    # and the local settings are ignored for extraction.
    extraction_agent_id: str | None = None


class JsonSchema(BaseModel):
    type: str = "object"
    properties: dict[str, Any] = {}
    required: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
