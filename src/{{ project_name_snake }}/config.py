import functools
import os

import dotenv
from llama_cloud_services import LlamaExtract

dotenv.load_dotenv()

# Add getters for clients and environment variables here.


@functools.lru_cache(maxsize=None)
def get_extract_api() -> LlamaExtract:
    return LlamaExtract(
        api_key=os.environ["LLAMA_CLOUD_API_KEY"],
    )


