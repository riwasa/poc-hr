import os
from azure.identity import DefaultAzureCredential
from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# Set up the client
endpoint = os.getenv("AI_SEARCH_ENDPOINT")
index_name = os.getenv("AI_SEARCH_INDEX_NAME")
credential = DefaultAzureCredential()

client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

# Query text used for both vector and keyword search
query_text = "what benefits are in my dental plan?"

# Create query_vector from a Microsoft Foundry embedding deployment.
foundry_endpoint = os.getenv("AI_SEARCH_FOUNDRY_ENDPOINT")
embedding_deployment = os.getenv("AI_SEARCH_FOUNDRY_EMBEDDING_DEPLOYMENT")

if not foundry_endpoint or not embedding_deployment:
    raise ValueError(
        "Missing Foundry configuration. Set FOUNDRY_ENDPOINT (or AZURE_OPENAI_ENDPOINT) "
        "and FOUNDRY_EMBEDDING_DEPLOYMENT (or AZURE_OPENAI_EMBEDDING_DEPLOYMENT)."
    )

# Prefer API key if provided; otherwise use Entra ID token auth.
api_key = os.getenv("AZURE_OPENAI_API_KEY")
if api_key:
    embedding_client = AzureOpenAI(
        azure_endpoint=foundry_endpoint,
        api_key=api_key,
        api_version="2024-06-01",
    )
else:
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )
    embedding_client = AzureOpenAI(
        azure_endpoint=foundry_endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-06-01",
    )

embedding_response = embedding_client.embeddings.create(
    model=embedding_deployment,
    input=query_text,
)
query_vector = embedding_response.data[0].embedding

# Create the vector query
vector_query = VectorizedQuery(
    vector=query_vector,
    k_nearest_neighbors=10,
    fields="content_embedding",
    exhaustive=True
)

# Execute hybrid search
results = client.search(
    search_text=query_text,
    vector_queries=[vector_query],
    select=["content_text", "content_path", "sourceurl"],
    top=10
)

for result in results:
    print(f"Content: {result['content_text']}")
    print(f"Content Path: {result['content_path']}")
    print(f"Source URL: {result['sourceurl']}")
