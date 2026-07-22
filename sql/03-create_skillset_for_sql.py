"""Create or update the sql-rag-skillset Azure AI Search skillset.

Required environment variables:
- AZURE_SEARCH_ENDPOINT: https://<search-service>.search.windows.net

Optional environment variables:
- AZURE_SEARCH_SKILLSET_NAME (default: sql-rag-skillset)
- AZURE_SEARCH_TARGET_INDEX_NAME (default: sql-rag)
- AZURE_OPENAI_RESOURCE_URI (default: https://rie-h1-hr-fnd-cae.openai.azure.com)
- AZURE_OPENAI_EMBEDDING_DEPLOYMENT_ID (default: text-embedding-3-large)
- AZURE_OPENAI_EMBEDDING_MODEL_NAME (default: text-embedding-3-large)
- AZURE_OPENAI_EMBEDDING_DIMENSIONS (default: 3072)
"""

from __future__ import annotations

import logging
import os
import sys

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
	AzureOpenAIEmbeddingSkill,
	IndexProjectionMode,
	InputFieldMappingEntry,
	OutputFieldMappingEntry,
	SearchIndexerIndexProjection,
	SearchIndexerIndexProjectionSelector,
	SearchIndexerIndexProjectionsParameters,
	SearchIndexerSkillset,
	SplitSkill,
)
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"  # one level up
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
	value = os.getenv(name)
	if not value:
		raise ValueError(f"Missing required environment variable: {name}")
	return value


def build_skillset() -> SearchIndexerSkillset:
	skillset_name = os.getenv("SQL_AI_SEARCH_SKILLSET_NAME")
	target_index_name = os.getenv("SQL_AI_SEARCH_INDEX_NAME")

	openai_resource_uri = os.getenv("SQL_FOUNDRY_ENDPOINT")
	openai_deployment_id = os.getenv("SQL_FOUNDRY_EMBEDDING_DEPLOYMENT")
	openai_model_name = os.getenv("SQL_FOUNDRY_EMBEDDING_MODEL_NAME")
	openai_dimensions = 3072

	split_skill = SplitSkill(
		name="#1",
		description="Split skill to chunk documents",
		context="/document",
		default_language_code="en",
		text_split_mode="pages",
		maximum_page_length=2000,
		page_overlap_length=500,
		maximum_pages_to_take=0,
		inputs=[InputFieldMappingEntry(name="text", source="/document/Description")],
		outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")],
	)

	embedding_skill = AzureOpenAIEmbeddingSkill(
		name="#2",
		context="/document/pages/*",
		resource_url=openai_resource_uri,
		deployment_name=openai_deployment_id,
		model_name=openai_model_name,
		dimensions=openai_dimensions,
		inputs=[InputFieldMappingEntry(name="text", source="/document/pages/*")],
		outputs=[OutputFieldMappingEntry(name="embedding", target_name="text_vector")],
	)

	selectors = [
		SearchIndexerIndexProjectionSelector(
			target_index_name=target_index_name,
			parent_key_field_name="parent_id",
			source_context="/document/pages/*",
			mappings=[
				InputFieldMappingEntry(
					name="text_vector",
					source="/document/pages/*/text_vector",
				),
				InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
				InputFieldMappingEntry(name="Id", source="/document/Id"),
				InputFieldMappingEntry(name="Title", source="/document/Title"),
				InputFieldMappingEntry(
					name="LocationName",
					source="/document/LocationName",
				),
				InputFieldMappingEntry(name="LocationId", source="/document/LocationId"),
				InputFieldMappingEntry(name="PostingDate", source="/document/PostingDate"),
				InputFieldMappingEntry(name="MinSalary", source="/document/MinSalary"),
				InputFieldMappingEntry(name="MaxSalary", source="/document/MaxSalary"),
				InputFieldMappingEntry(name="IsActive", source="/document/IsActive"),
			],
		)
	]

	index_projections = SearchIndexerIndexProjection(
		selectors=selectors,
		parameters=SearchIndexerIndexProjectionsParameters(
			projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
		),
	)

	skillset_kwargs = {
		"name": skillset_name,
		"description": "Skillset to chunk documents and generate embeddings",
		"skills": [split_skill, embedding_skill],
	}

	# SDK compatibility: older azure-search-documents uses `index_projection`, newer uses
	# `index_projections`.
	try:
		return SearchIndexerSkillset(
			index_projections=index_projections,
			**skillset_kwargs,
		)
	except TypeError as exc:
		if "unexpected keyword argument 'index_projections'" not in str(exc):
			raise
		return SearchIndexerSkillset(
			index_projection=index_projections,
			**skillset_kwargs,
		)


def main() -> int:
	try:
		endpoint = os.getenv("AI_SEARCH_ENDPOINT")
		credential = DefaultAzureCredential()
		client = SearchIndexerClient(endpoint=endpoint, credential=credential)

		skillset = build_skillset()
		created = client.create_or_update_skillset(skillset)
		logger.info("Skillset created or updated: %s", created.name)
		return 0
	except ValueError as exc:
		logger.error("Configuration error: %s", exc)
		return 2
	except HttpResponseError as exc:
		logger.error("Azure Search request failed: %s", exc)
		return 1


if __name__ == "__main__":
	sys.exit(main())
