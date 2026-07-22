"""Create or update the sql-rag Azure AI Search index using the Python SDK.

Required environment variables:
- AZURE_SEARCH_ENDPOINT: https://<search-service>.search.windows.net

Optional environment variables:
- AZURE_SEARCH_INDEX_NAME (default: sql-rag)
- AZURE_OPENAI_RESOURCE_URI (default: https://rie-h1-hr-fnd-cae.openai.azure.com)
- AZURE_OPENAI_EMBEDDING_DEPLOYMENT_ID (default: text-embedding-3-large)
- AZURE_OPENAI_EMBEDDING_MODEL_NAME (default: text-embedding-3-large)
- AZURE_OPENAI_API_KEY (optional; only needed if your vectorizer is key-based)
"""

from __future__ import annotations

import logging
import os
import sys

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
	AzureOpenAIVectorizer,
	AzureOpenAIVectorizerParameters,
	BM25SimilarityAlgorithm,
	HnswAlgorithmConfiguration,
	HnswParameters,
	SearchField,
	SearchFieldDataType,
	SearchIndex,
	SearchableField,
	SemanticConfiguration,
	SemanticField,
	SemanticPrioritizedFields,
	SemanticSearch,
	SimpleField,
	VectorSearch,
	VectorSearchProfile,
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


def build_index() -> SearchIndex:
	index_name = os.getenv("SQL_AI_SEARCH_INDEX_NAME")
	embedding_profile_name = "sql-embedding-profile"
	embedding_vectorizer_name = "sql-embedding-vectorizer"
	embedding_algorithm_name = "sql-embedding-algorithm"

	openai_resource_uri = os.getenv("SQL_FOUNDRY_ENDPOINT")
	openai_deployment_id = os.getenv("SQL_FOUNDRY_EMBEDDING_DEPLOYMENT")
	openai_model_name = os.getenv("SQL_FOUNDRY_EMBEDDING_MODEL_NAME")
	openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")

	fields = [
		SearchableField(
			name="chunk_id",
			type=SearchFieldDataType.String,
			key=True,
			sortable=True,
			analyzer_name="keyword",
		),
		SimpleField(
			name="parent_id",
			type=SearchFieldDataType.String,
			filterable=True,
		),
		SearchableField(name="chunk", type=SearchFieldDataType.String),
		SearchField(
			name="text_vector",
			type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
			searchable=True,
			retrievable=True,
			vector_search_dimensions=3072,
			vector_search_profile_name=embedding_profile_name,
		),
		SearchableField(name="Id", type=SearchFieldDataType.String),
		SearchableField(name="Title", type=SearchFieldDataType.String),
		SearchableField(
			name="LocationName",
			type=SearchFieldDataType.String,
			filterable=True,
		),
		SimpleField(
			name="LocationId",
			type=SearchFieldDataType.Int32,
			filterable=True,
		),
		SimpleField(
			name="PostingDate",
			type=SearchFieldDataType.DateTimeOffset,
			filterable=True,
		),
		SimpleField(
			name="MinSalary",
			type=SearchFieldDataType.Double,
			filterable=True,
		),
		SimpleField(
			name="MaxSalary",
			type=SearchFieldDataType.Double,
			filterable=True,
		),
		SimpleField(
			name="IsActive",
			type=SearchFieldDataType.Boolean,
			filterable=True,
		),
	]

	vectorizer_params = AzureOpenAIVectorizerParameters(
		resource_url=openai_resource_uri,
		deployment_name=openai_deployment_id,
		model_name=openai_model_name,
		api_key=openai_api_key,
	)

	index = SearchIndex(
		name=index_name,
		fields=fields,
		similarity=BM25SimilarityAlgorithm(),
		semantic_search=SemanticSearch(
			default_configuration_name="sql-semantic-configuration",
			configurations=[
				SemanticConfiguration(
					name="sql-semantic-configuration",
					prioritized_fields=SemanticPrioritizedFields(
						content_fields=[SemanticField(field_name="chunk")],
						keywords_fields=[],
					),
				)
			],
		),
		vector_search=VectorSearch(
			algorithms=[
				HnswAlgorithmConfiguration(
					name=embedding_algorithm_name,
					parameters=HnswParameters(
						metric="cosine",
						m=4,
						ef_construction=400,
						ef_search=500,
					),
				)
			],
			profiles=[
				VectorSearchProfile(
					name=embedding_profile_name,
					algorithm_configuration_name=embedding_algorithm_name,
					vectorizer_name=embedding_vectorizer_name,
				)
			],
			vectorizers=[
				AzureOpenAIVectorizer(
					vectorizer_name=embedding_vectorizer_name,
					parameters=vectorizer_params,
				)
			],
		),
	)

	return index


def main() -> int:
	try:
		endpoint = os.getenv("AI_SEARCH_ENDPOINT")
		credential = DefaultAzureCredential()
		client = SearchIndexClient(endpoint=endpoint, credential=credential)

		index = build_index()
		created = client.create_or_update_index(index)
		logger.info("Index created or updated: %s", created.name)
		return 0
	except ValueError as exc:
		logger.error("Configuration error: %s", exc)
		return 2
	except HttpResponseError as exc:
		logger.error("Azure Search request failed: %s", exc)
		return 1


if __name__ == "__main__":
	sys.exit(main())
