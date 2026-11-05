import json
import os
from contextlib import contextmanager
from pathlib import Path

from azure.core.exceptions import AzureError
from azure.identity import EnvironmentCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI, OpenAIError

from app.schema import response_schema


@contextmanager
def llm_connection():
    """Yield a client and model name, then close the connection resources."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider not in ("openai", "azure"):
        raise ValueError("LLM_PROVIDER must be openai or azure.")

    required = ["OPENAI_API_KEY"]
    if provider == "azure":
        required = [
            "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
            "AZURE_OPENAI_TOKEN_SCOPE", "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT",
        ]
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise ValueError("Missing settings: " + ", ".join(missing))

    if provider == "openai":
        model = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        with OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60, max_retries=1) as client:
            yield client, model
        return

    with EnvironmentCredential() as credential:
        token_provider = get_bearer_token_provider(
            credential, os.environ["AZURE_OPENAI_TOKEN_SCOPE"]
        )

        def azure_token():
            # Keep authentication failures compatible with the pipeline's API error handling.
            try:
                return token_provider()
            except AzureError:
                raise OpenAIError("Azure authentication failed. Check credentials and proxy settings.") from None

        with AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            azure_ad_token_provider=azure_token,
            timeout=60,
            max_retries=1,
        ) as client:
            yield client, os.environ["AZURE_OPENAI_DEPLOYMENT"]


def request_classification(client, model, fields, prompt):
    try:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    except ValueError:
        raise ValueError("LLM_TEMPERATURE must be a number between 0 and 2.") from None
    if not 0 <= temperature <= 2:
        raise ValueError("LLM_TEMPERATURE must be a number between 0 and 2.")

    schema = response_schema()
    return client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(fields, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "Classification", "strict": True, "schema": schema},
        },
        temperature=temperature,
        store=False,
    )
