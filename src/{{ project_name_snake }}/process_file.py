import logging

from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent
from workflows.retry_policy import ConstantDelayRetryPolicy

logger = logging.getLogger(__name__)


class FileEvent(StartEvent):
    file_id: str


class ProcessFileWorkflow(Workflow):
    """
    Given a file path, this workflow will process a single file through the custom extraction logic.
    """

    @step(retry_policy=ConstantDelayRetryPolicy(maximum_attempts=3, delay=10))
    async def run_file(self, event: FileEvent) -> StopEvent:
        logger.info(f"Processing file {event.file_path}")
        # TODO: process the file
        return StopEvent()
