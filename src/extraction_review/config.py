"""
Configuration for the extraction review application.

Configuration is loaded from configs/config.json via ResourceConfig.
Each top-level key in config.json maps to an SDK product-configuration type:
the discriminated union members returned by `client.configurations.retrieve`.
Each template-side subclass adds an optional `configuration_id` so a key
can either carry an inline snapshot OR point at a saved platform config.
"""

import logging

from llama_cloud.types.beta.split_category import SplitCategory
from llama_cloud.types.classify_v2_parameters import ClassifyV2Parameters, Rule
from llama_cloud.types.extract_v2_parameters import ExtractV2Parameters
from llama_cloud.types.parse_v2_parameters import ParseV2Parameters
from llama_cloud.types.split_v1_parameters import SplitV1Parameters
from pydantic import BaseModel

from .json_util import get_extraction_schema as get_extraction_schema

logger = logging.getLogger(__name__)


# The name of the collection to use for storing extracted data.
EXTRACTED_DATA_COLLECTION: str = "extraction-review"


class ExtractConfig(ExtractV2Parameters):
    """Extract product configuration.

    Inherits the SDK `ExtractV2Parameters` shape (product_type="extract_v2",
    data_schema, tier, cite_sources, confidence_scores, extraction_target, ...).
    Set `configuration_id` to a saved LlamaCloud configuration id (cfg-...)
    to pull the parameters from the platform instead of using the local values.
    """

    configuration_id: str | None = None


class ClassifyConfig(ClassifyV2Parameters):
    """Classify product configuration.

    Inherits the SDK `ClassifyV2Parameters` shape. Overrides `rules` default
    to `[]` so an unused classify slot validates without a rule list.
    """

    rules: list[Rule] = []
    configuration_id: str | None = None


class ParseConfig(ParseV2Parameters):
    """Parse product configuration.

    Inherits the SDK `ParseV2Parameters` shape (product_type="parse_v2",
    tier, version, plus structured option groups).
    """

    configuration_id: str | None = None


class SplitConfig(SplitV1Parameters):
    """Split product configuration.

    Inherits the SDK `SplitV1Parameters` shape. Overrides `categories` default
    to `[]` so an unused split slot validates without categories.
    """

    categories: list[SplitCategory] = []
    configuration_id: str | None = None


class Config(BaseModel):
    """Root configuration model for configs/config.json."""

    extract: ExtractConfig
    classify: ClassifyConfig
    parse: ParseConfig
    split: SplitConfig
