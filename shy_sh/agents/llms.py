from shy_sh.settings import settings, BaseLLMSchema
from functools import lru_cache


@lru_cache
def get_llm():
    return _get_llm(settings.llm)


def _get_llm(llm_config: BaseLLMSchema):
    llm = None
    match llm_config.provider:
        case "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=llm_config.name,
                temperature=llm_config.temperature,
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
            )
        case "ollama":
            from langchain_ollama import ChatOllama

            llm = ChatOllama(model=llm_config.name, temperature=llm_config.temperature)

        case "groq":
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                model=llm_config.name,
                temperature=llm_config.temperature,
                api_key=llm_config.api_key,
            )

        case "anthropic":
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(
                model_name=llm_config.name,
                temperature=llm_config.temperature,
                anthropic_api_key=llm_config.api_key,
            )

        case "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            import os

            # Suppress logging warnings
            os.environ["GRPC_VERBOSITY"] = "ERROR"
            os.environ["GLOG_minloglevel"] = "2"

            llm = ChatGoogleGenerativeAI(
                model=llm_config.name,
                temperature=llm_config.temperature,
                api_key=llm_config.api_key,
            )

        case "aws":
            from langchain_aws import ChatBedrockConverse

            region, access_key, secret_key = llm_config.api_key.split(" ")

            llm = ChatBedrockConverse(
                model=llm_config.name,
                temperature=llm_config.temperature,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        case _:
            raise ValueError(f"Unknown LLM provider: {llm_config.provider}")
    return llm


DEFAULT_CONTEXT_LEN = 8192
LLM_CONTEXT_WINDOWS = {
    "openai": {
        "default": DEFAULT_CONTEXT_LEN * 4,
    },
    "ollama": {
        "default": DEFAULT_CONTEXT_LEN,
    },
    "groq": {
        "default": DEFAULT_CONTEXT_LEN,
    },
    "anthropic": {
        "default": DEFAULT_CONTEXT_LEN * 4,
    },
    "google": {
        "default": DEFAULT_CONTEXT_LEN * 4,
    },
    "aws": {
        "default": DEFAULT_CONTEXT_LEN * 4,
    },
}


def get_llm_context():
    provider = LLM_CONTEXT_WINDOWS.get(settings.llm.provider, None)
    if not provider:
        return DEFAULT_CONTEXT_LEN
    return provider.get(
        settings.llm.name,
        provider.get("default", DEFAULT_CONTEXT_LEN),
    )
