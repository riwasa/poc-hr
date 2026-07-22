import os
from azure.identity import DefaultAzureCredential
from azure.ai.textanalytics import TextAnalyticsClient
from dotenv import load_dotenv

load_dotenv()

# Caller requires Cognitive Services User role on the Language resource.

endpoint = os.environ["LANGUAGE_ENDPOINT"]

text_analytics_client = TextAnalyticsClient(
    endpoint=endpoint, credential=DefaultAzureCredential()
)
documents = [
        """Parker Doe has repaid all of their loans as of 2020-04-25.
        Their SSN is 859-98-0987. To contact them, use their phone number
        555-555-5555. They are originally from Brazil and have Brazilian CPF number 998.214.865-68"""
    ]

result = text_analytics_client.recognize_pii_entities(documents)
docs = [doc for doc in result if not doc.is_error]

print(
    "Let's compare the original document with the documents after redaction. "
    "I also want to comb through all of the entities that got redacted"
)
for idx, doc in enumerate(docs):
    print(f"Document text: {documents[idx]}")
    print(f"Redacted document text: {doc.redacted_text}")
    for entity in doc.entities:
        print("...Entity '{}' with category '{}' got redacted".format(
            entity.text, entity.category
        ))

# [END recognize_pii_entities]
print("All of the information that I expect to be redacted is!")

print(
    "Now I want to explicitly extract SSN information to add to my user SSN database. "
    "I also want to be fairly confident that what I'm storing is an SSN, so let's also "
    "ensure that we're > 60% positive the entity is a SSN"
)
social_security_numbers = []
for doc in docs:
    for entity in doc.entities:
        if entity.category == 'USSocialSecurityNumber' and entity.confidence_score >= 0.6:
            social_security_numbers.append(entity.text)

print("We have extracted the following SSNs as well: '{}'".format(
    "', '".join(social_security_numbers)
))