import functools
import os

import dotenv
from extracted_data_client import AuthenticatedClient
from llama_cloud_services import LlamaExtract

dotenv.load_dotenv()


@functools.lru_cache(maxsize=None)
def get_extract_api() -> LlamaExtract:
    return LlamaExtract(
        api_key=os.environ["LLAMA_CLOUD_API_KEY"],
        project_id=os.environ.get("LLAMA_CLOUD_PROJECT_ID", None),
    )


@functools.lru_cache(maxsize=None)
def get_extracted_data_client():
    return AuthenticatedClient(
        base_url=os.environ.get("EXTRACTED_DATA_BASE_URL", "http://localhost:9182"),
        token=os.environ["EXTRACTED_DATA_TOKEN"],
    )
