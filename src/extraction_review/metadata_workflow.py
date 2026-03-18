from typing import Annotated, Any

import jsonref
from llama_cloud import AsyncLlamaCloud
from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent
from workflows.resource import Resource, ResourceConfig

from .clients import get_llama_cloud_client
from .config import EXTRACTED_DATA_COLLECTION, ExtractConfig, JsonSchema


class MetadataResponse(StopEvent):
    json_schema: dict[str, Any]
    extracted_data_collection: str


class MetadataWorkflow(Workflow):
    """Provide extraction schema and configuration to the workflow editor."""

    @step
    async def get_metadata(
        self,
        _: StartEvent,
        extraction_schema: Annotated[
            JsonSchema,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract.json_schema",
                label="Extraction Schema",
                description="JSON Schema defining the fields to extract from documents",
            ),
        ],
        extract_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract",
                label="Extraction Settings",
                description="Configuration for document extraction quality and features",
            ),
        ],
        llama_cloud_client: Annotated[
            AsyncLlamaCloud, Resource(get_llama_cloud_client)
        ],
    ) -> MetadataResponse:
        """Return the data schema and storage settings for the review interface.

        When extraction_agent_id is set, fetches the schema from the remote
        agent so the UI always reflects what the agent will actually extract.
        Otherwise uses the local schema from config.json.
        """
        if extract_config.extraction_agent_id:
            agent = await llama_cloud_client.extraction.extraction_agents.get(
                extract_config.extraction_agent_id
            )
            schema_dict = agent.data_schema
        else:
            schema_dict = extraction_schema.to_dict()

        json_schema = jsonref.replace_refs(schema_dict, proxies=False)
        return MetadataResponse(
            json_schema=json_schema,
            extracted_data_collection=EXTRACTED_DATA_COLLECTION,
        )


workflow = MetadataWorkflow(timeout=None)
