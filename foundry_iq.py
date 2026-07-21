import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeRetrievalSemanticIntent,
    KnowledgeBaseRetrievalRequest,
    AzureBlobKnowledgeSourceParams,
    #SearchIndexKnowledgeSourceParams,
)
from dotenv import load_dotenv

load_dotenv()

# Create knowledge base retrieval client
kb_client = KnowledgeBaseRetrievalClient(
    endpoint=os.getenv("FOUNDRY_IQ_ENDPOINT"),
    knowledge_base_name=os.getenv("FOUNDRY_IQ_KNOWLEDGE_BASE_NAME"),
    credential=DefaultAzureCredential(),
)

request = KnowledgeBaseRetrievalRequest(
    intents=[
        KnowledgeRetrievalSemanticIntent(
            search="What does my dental plan include?"
        )
    ],
    # knowledge_source_params=[
    #     AzureBlobKnowledgeSourceParams(
    #         knowledge_source_name=os.getenv("FOUNDRY_IQ_KNOWLEDGE_SOURCE_NAME"),
    #     )
    # ],
)

result = kb_client.retrieve(request)
print(result.response[0].content[0].text)