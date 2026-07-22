"""Create or update the sql-rag Azure AI Search datasource using the Python SDK.

Prompts for the Azure SQL username and password on the command line.

Optional environment variables:
- AZURE_SEARCH_DATASOURCE_NAME (default: sql-rag-datasource)
- SQL_TABLE_QUERY (optional: custom SELECT query for the SQL indexer)
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import SearchIndexerDataContainer, SearchIndexerDataSourceConnection
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"  # one level up
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_TABLE = os.getenv("SQL_TABLE")


def _default_table_query(table_name: str) -> str:
	"""Build a default query that normalizes SQL types for Azure AI Search."""
	return (
		"SELECT "
		"CAST([Id] AS nvarchar(50)) AS [Id], "
		"[Title], "
		"[Description], "
		"[LocationName], "
		"[LocationId], "
		"[PostingDate], "
		"CAST([MinSalary] AS float) AS [MinSalary], "
		"CAST([MaxSalary] AS float) AS [MaxSalary], "
		"[IsActive] "
		f"FROM [dbo].[{table_name}]"
	)

def _prompt_username(args: argparse.Namespace) -> str:
	username = args.username or input("SQL username: ").strip()
	if not username:
		raise ValueError("SQL username is required")
	return username


def _prompt_password(args: argparse.Namespace) -> str:
	password = args.password or getpass.getpass("SQL password: ")
	if not password:
		raise ValueError("SQL password is required")
	return password


def _build_connection_string(username: str, password: str) -> str:
	return (
		f"Data Source={SQL_SERVER};"
		f"Initial Catalog={SQL_DATABASE};"
		f"User ID={username};"
		f"Password={password};"
		"Connect Timeout=30;"
		"Encrypt=True;"
		"Trust Server Certificate=False"
	)


def build_datasource(username: str, password: str) -> SearchIndexerDataSourceConnection:
	datasource_name = os.getenv("SQL_AI_SEARCH_DATASOURCE_NAME")
	table_query = os.getenv("SQL_TABLE_QUERY") or _default_table_query(SQL_TABLE)

	return SearchIndexerDataSourceConnection(
		name=datasource_name,
		type="azuresql",
		connection_string=_build_connection_string(username, password),
		container=SearchIndexerDataContainer(name=SQL_TABLE, query=table_query),
	)


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Create or update the Azure AI Search datasource for SQL job postings."
	)
	parser.add_argument(
		"--username",
		help="Azure SQL username. If omitted, you will be prompted.",
	)
	parser.add_argument(
		"--password",
		help="Azure SQL password. If omitted, you will be prompted securely.",
	)
	return parser.parse_args()


def main() -> int:
	try:
		args = _parse_args()
		username = _prompt_username(args)
		password = _prompt_password(args)

		credential = DefaultAzureCredential()
		client = SearchIndexerClient(endpoint=SEARCH_ENDPOINT, credential=credential)

		datasource = build_datasource(username, password)
		created = client.create_or_update_data_source_connection(datasource)
		logger.info("Datasource created or updated: %s", created.name)
		return 0
	except ValueError as exc:
		logger.error("Configuration error: %s", exc)
		return 2
	except HttpResponseError as exc:
		logger.error("Azure Search request failed: %s", exc)
		return 1


if __name__ == "__main__":
	sys.exit(main())
