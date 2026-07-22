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
index_name = 'rag-1784735356357' #os.getenv("AI_SEARCH_INDEX_NAME")
credential = DefaultAzureCredential()

client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

# Query text used for both vector and keyword search
query_text = "what management postings are there?"
location_id_raw = os.getenv("AI_SEARCH_LOCATION_ID", "1")
location_id = int(location_id_raw) if location_id_raw else None
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
search_filter = f"LocationId eq {location_id}" if location_id is not None else None

results = client.search(
    search_text=query_text,
    vector_queries=[vector_query],
    filter=search_filter,
    select=["Id", "Title", "LocationName", "LocationId", "PostingDate", "MinSalary", "MaxSalary", "IsActive"],
    top=10
)

for result in results:
    print(f"Id: {result['Id']}")
    print(f"Title: {result['Title']}")
    print(f"Location Name: {result['LocationName']}")
    print(f"Location Id: {result['LocationId']}")
    print(f"Posting Date: {result['PostingDate']}")
    print(f"Min Salary: {result['MinSalary']}")
    print(f"Max Salary: {result['MaxSalary']}")
    print(f"Is Active: {result['IsActive']}")

