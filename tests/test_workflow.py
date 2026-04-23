import json
from pathlib import Path

import pytest
from extraction_review.config import EXTRACTED_DATA_COLLECTION
from extraction_review.metadata_workflow import MetadataResponse
from extraction_review.metadata_workflow import workflow as metadata_workflow
from extraction_review.process_file import FileEvent
from extraction_review.process_file import workflow as process_file_workflow
from llama_cloud_fake import FakeLlamaCloudServer
from workflows.events import StartEvent


def get_extraction_schema() -> dict:
    """Load the extraction schema from the unified config file."""
    config_path = Path(__file__).parent.parent / "configs" / "config.json"
    config = json.loads(config_path.read_text())
    return config["extract"]["data_schema"]


@pytest.mark.asyncio
async def test_process_file_workflow(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeLlamaCloudServer,
) -> None:
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "fake-api-key")
    file_id = fake.files.preload(path="tests/files/test.pdf")
    try:
        result = await process_file_workflow.run(start_event=FileEvent(file_id=file_id))
    except Exception:
        result = None
    assert result is not None
    # all generated agent data IDs are alphanumeric strings with 7 characters
    assert isinstance(result, str)
    assert len(result) == 7


@pytest.mark.asyncio
async def test_metadata_workflow() -> None:
    result = await metadata_workflow.run(start_event=StartEvent())
    assert isinstance(result, MetadataResponse)
    assert result.extracted_data_collection == EXTRACTED_DATA_COLLECTION
    assert result.json_schema == get_extraction_schema()
