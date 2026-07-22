"""Create or update the sql-rag Azure AI Search indexer using the Python SDK.

Required environment variables:
- AZURE_SEARCH_ENDPOINT: https://<search-service>.search.windows.net

Optional environment variables:
- AZURE_SEARCH_INDEXER_NAME (default: sql-rag-new-indexer)
- AZURE_SEARCH_DATASOURCE_NAME (default: sql-rag-new-datasource)
- AZURE_SEARCH_INDEX_NAME (default: sql-rag-new)
- AZURE_SEARCH_SKILLSET_NAME (default: sql-rag-new-skillset)
- AZURE_SEARCH_RUN_INDEXER (default: false)
"""

from __future__ import annotations

import logging
import os
import sys

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import FieldMapping, SearchIndexer
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


def _to_bool(value: str | None) -> bool:
	if value is None:
		return False
	return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def build_indexer() -> SearchIndexer:
	indexer_name = os.getenv("SQL_AI_SEARCH_INDEXER_NAME")
	datasource_name = os.getenv("SQL_AI_SEARCH_DATASOURCE_NAME")
	index_name = os.getenv("SQL_AI_SEARCH_INDEX_NAME")
	skillset_name = os.getenv("SQL_AI_SEARCH_SKILLSET_NAME")

	return SearchIndexer(
		name=indexer_name,
		description="Indexer for SQL RAG documents with chunking and embeddings",
		data_source_name=datasource_name,
		target_index_name=index_name,
		skillset_name=skillset_name,
		field_mappings=[
			# Required for indexer validation because the index key is `chunk_id`
			# while the SQL source key column is `Id`.
			FieldMapping(source_field_name="Id", target_field_name="chunk_id")
		],
	)


def main() -> int:
	try:
		endpoint = os.getenv("AI_SEARCH_ENDPOINT")
		credential = DefaultAzureCredential()
		client = SearchIndexerClient(endpoint=endpoint, credential=credential)

		indexer = build_indexer()
		created = client.create_or_update_indexer(indexer)
		logger.info("Indexer created or updated: %s", created.name)

		if _to_bool(os.getenv("AZURE_SEARCH_RUN_INDEXER", "false")):
			client.run_indexer(created.name)
			logger.info("Indexer execution started: %s", created.name)

		return 0
	except ValueError as exc:
		logger.error("Configuration error: %s", exc)
		return 2
	except HttpResponseError as exc:
		logger.error("Azure Search request failed: %s", exc)
		return 1


if __name__ == "__main__":
	sys.exit(main())
