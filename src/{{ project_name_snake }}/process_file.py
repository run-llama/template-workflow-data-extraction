import asyncio
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Literal

import httpx
from llama_cloud import ExtractRun
from pydantic import ValidationError
from llama_cloud_services.extract import SourceText
from llama_cloud_services.beta.agent_data import ExtractedData
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent
from workflows.retry_policy import ConstantDelayRetryPolicy

from .config import get_llama_cloud_client, get_data_client, get_extract_agent
from .schemas import MySchema

logger = logging.getLogger(__name__)


class FileEvent(StartEvent):
    file_id: str


class DownloadFileEvent(Event):
    file_id: str


class FileDownloadedEvent(Event):
    file_id: str
    file_path: str
    filename: str


class UIToast(Event):
    level: Literal["info", "warning", "error"]
    message: str


class ExtractedEvent(Event):
    file_id: str
    file_path: str
    filename: str
    extracted: MySchema
    confidence: dict[str, dict | float]


class ExtractedInvalidEvent(Event):
    file_id: str
    file_path: str
    filename: str
    extracted: dict[str, Any]
    confidence: dict[str, dict | float]


class ProcessFileWorkflow(Workflow):
    """
    Given a file path, this workflow will process a single file through the custom extraction logic.
    """

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def run_file(self, event: FileEvent) -> DownloadFileEvent:
        logger.info(f"Running file {event.file_id}")
        return DownloadFileEvent(file_id=event.file_id)

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def download_file(
        self, event: DownloadFileEvent, ctx: Context
    ) -> FileDownloadedEvent:
        try:
            file_metadata = await get_llama_cloud_client().files.get_file(
                id=event.file_id
            )
            file_url = await get_llama_cloud_client().files.read_file_content(
                event.file_id
            )

            temp_dir = tempfile.gettempdir()
            filename = file_metadata.name
            file_path = os.path.join(temp_dir, filename)
            client = httpx.AsyncClient()
            # Report progress to the UI
            logger.info(f"Downloading file {file_url.url} to {file_path}")
            ctx.write_event_to_stream(
                UIToast(
                    level="info",
                    message=f"Downloading file {file_url.url} to {file_path}",
                )
            )

            async with client.stream("GET", file_url.url) as response:
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            logger.info(f"Downloaded file {file_url.url} to {file_path}")
            return FileDownloadedEvent(
                file_id=event.file_id, file_path=file_path, filename=filename
            )
        except Exception as e:
            logger.error(f"Error downloading file {event.file_id}: {e}", exc_info=True)
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error downloading file {event.file_id}: {e}",
                )
            )
            raise e

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def process_file(
        self, event: FileDownloadedEvent, ctx: Context
    ) -> ExtractedEvent | ExtractedInvalidEvent:
        try:
            agent = get_extract_agent()
            source_text = SourceText(
                file=event.file_path,
                filename=event.filename,
            )
            logger.info(f"Extracting data from file {event.filename}")
            ctx.write_event_to_stream(
                UIToast(
                    level="info", message=f"Extracting data from file {event.filename}"
                )
            )
            extracted_result: ExtractRun = await agent.aextract(source_text)
            try:
                logger.info(f"Extracted data: {extracted_result}")
                extracted = MySchema.model_validate(extracted_result.data)
                return ExtractedEvent(
                    file_id=event.file_id,
                    file_path=event.file_path,
                    filename=event.filename,
                    extracted=extracted,
                    confidence=get_confidence(extracted_result),
                )
            except ValidationError as e:
                return ExtractedInvalidEvent(
                    file_id=event.file_id,
                    file_path=event.file_path,
                    filename=event.filename,
                    extracted=extracted_result.data,
                    confidence=get_confidence(extracted_result),
                )
        except Exception as e:
            logger.error(
                f"Error extracting data from file {event.filename}: {e}",
                exc_info=True,
            )
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error extracting data from file {event.filename}: {e}",
                )
            )
            raise e

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def record_extracted_data(
        self, event: ExtractedEvent | ExtractedInvalidEvent, ctx: Context
    ) -> StopEvent:
        try:
            logger.info(f"Recorded extracted data for file {event.filename}")
            ctx.write_event_to_stream(
                UIToast(
                    level="info",
                    message=f"Recorded extracted data for file {event.filename}",
                )
            )
            item_id = await get_data_client().create_item(
                ExtractedData.create(
                    data=event.extracted,
                    status="pending_review"
                    if isinstance(event, ExtractedEvent)
                    else "error",
                    file_id=event.file_id,
                    file_name=event.filename,
                    file_hash=event.file_path,
                    confidence=event.confidence,
                )
            )
            return StopEvent(
                result=item_id.id,
            )
        except Exception as e:
            logger.error(
                f"Error recording extracted data for file {event.filename}: {e}",
                exc_info=True,
            )
            ctx.write_event_to_stream(
                UIToast(
                    level="error",
                    message=f"Error recording extracted data for file {event.filename}: {e}",
                )
            )
            raise e


# extraction_metadata={'field_metadata': {'hello': {'citation': [{'page': 1, 'matching_text': '# Invoice Summary'}], 'extraction_confidence': 0.01, 'confidence': 0.01}, 'nested': {'foo': {'citation': [{'page': 1, 'matching_text': 'LINCOLNSHIRE AND DISTRICT MEDICAL SERVICES LTD'}], 'extraction_confidence': 0.01, 'confidence': 0.01}, 'bar': {'citation': [{'page': 1, 'matching_text': 'BEV/WITH/BRID HOSP COVER FEB 17'}], 'extraction_confidence': 0.01, 'confidence': 0.01}}}, 'usage': {'num_pages_extracted': 1, 'num_document_tokens': 364, 'num_output_tokens': 112}}
def get_confidence(extract_run: ExtractRun) -> dict[str, dict | float]:
    return get_confidence_recursive(extract_run.extraction_metadata["field_metadata"])


def get_confidence_recursive(metadata: dict[str, Any]) -> dict[str, dict | float]:
    response = {}
    for key, value in metadata.items():
        assert isinstance(value, dict)
        if "confidence" in value:
            response[key] = value["confidence"]
        else:
            response[key] = get_confidence_recursive(value)
    return response


workflow = ProcessFileWorkflow(timeout=None)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        file = await get_llama_cloud_client().files.upload_file(
            upload_file=Path("test.pdf").open("rb")
        )
        await workflow.run(start_event=FileEvent(file_id=file.id))

    asyncio.run(main())
