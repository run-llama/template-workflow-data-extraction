import asyncio
import logging

from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

logger = logging.getLogger(__name__)


class ProcessFile(Event):
    file_path: str
    total_files: int


class ProcessFileCompleted(Event):
    total_files: int
    did_succeed: bool


LOOP_SLEEP_TIME = 60


class LoopFiles(Workflow):
    """
    This workflow is a simple loop that processes all files in the data directory.
    It will process the files in parallel, and then sleep for a configurable amount of time.
    """

    @step
    async def start(self, event: StartEvent, ctx: Context) -> StartEvent | StopEvent:
        logger.info("Checking for files to process")
        # Get the files to process
        # check if they have already been processed
        # process the files that haven't been processed
        # sleep a bit
        await asyncio.sleep(LOOP_SLEEP_TIME)
        return StartEvent()

workflow = LoopFiles(timeout=None)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)


    async def main():
        await workflow.run()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
