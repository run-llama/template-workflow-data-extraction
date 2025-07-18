import logging
import os
import tempfile
from typing import Literal

import httpx
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


class ProcessFileWorkflow(Workflow):
    """
    Given a file path, this workflow will process a single file through the custom extraction logic.
    """

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def run_file(self, event: FileEvent) -> DownloadFileEvent:
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
    ) -> ExtractedEvent:
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
            extracted_result = await agent.aextract(source_text)
            extracted = MySchema.model_validate(extracted_result.data)
            return ExtractedEvent(
                file_id=event.file_id,
                file_path=event.file_path,
                filename=event.filename,
                extracted=extracted,
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
        self, event: ExtractedEvent, ctx: Context
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
                    status="pending_review",
                    file_id=event.file_id,
                    file_name=event.filename,
                    file_hash=event.file_path,
                )
            )
            logger.info(f"Recorded extracted data for file {event.filename}")
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


workflow = ProcessFileWorkflow(timeout=None)

