import os
import yaml

from typing import Type, Any, Literal

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from pydantic import BaseModel
from pathlib import Path
from questionary import confirm, text, select, password, Style


class BaseLLMSchema(BaseModel):
    provider: str
    name: str
    api_key: str = ""
    temperature: float = 0.0


class LLMSchema(BaseLLMSchema):
    agent_pattern: Literal["function_call", "react"] = "react"


class _Settings(BaseModel):
    llm: LLMSchema = LLMSchema(provider="ollama", name="llama3.2")

    vision_llm: BaseLLMSchema | None = None

    language: str = ""


class Settings(BaseSettings, _Settings):
    model_config = SettingsConfigDict(
        yaml_file=[
            "~/.config/shy/config.yaml",
            "~/.config/shy/config.yml",
            "./shy.yaml",
            "./shy.yml",
        ]
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        **kwargs: Any,
    ):
        return (YamlConfigSettingsSource(settings_cls),)


settings = Settings()
PROVIDERS = ["ollama", "openai", "google", "anthropic", "groq", "aws"]


def get_or_create_settings_path():
    file_name = None
    for f in reversed(settings.model_config["yaml_file"]):  # type: ignore
        f = Path(f).expanduser()
        if os.path.exists(f):
            file_name = f
            break
    if not file_name:
        file_name = settings.model_config["yaml_file"][0]  # type: ignore
        file_name = Path(file_name).expanduser()
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
    return file_name


_text_style = {
    "qmark": "",
    "style": Style.from_dict(
        {
            "selected": "fg:darkorange noreverse",
            "question": "fg:ansigreen nobold",
            "highlighted": "fg:darkorange",
            "text": "fg:darkorange",
            "answer": "fg:darkorange nobold",
            "instruction": "fg:darkorange",
        }
    ),
}

_select_style = {
    "pointer": "►",
    "instruction": " ",
    **_text_style,
}


def _try_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return "Please enter a valid number"


def configure_yaml():
    provider = select(
        message="Provider:",
        choices=PROVIDERS,
        default=settings.llm.provider,
        **_select_style,
    ).unsafe_ask()
    if provider != "ollama":
        api_key = password(
            message="API Key:",
            default=settings.llm.api_key,
            **_text_style,
        ).unsafe_ask()
    else:
        api_key = settings.llm.api_key
    model = input_model(provider, api_key, settings.llm.name)
    agent_pattern = select(
        message="Agent Pattern:",
        choices=["function_call", "react"],
        default=settings.llm.agent_pattern,
        **_select_style,
    ).unsafe_ask()
    temperature = text(
        message="Temperature:",
        default=str(settings.llm.temperature),
        validate=lambda x: _try_float(x),
        **_text_style,
    ).unsafe_ask()

    llm = {
        "provider": provider,
        "name": model,
        "api_key": api_key,
        "temperature": float(temperature),
        "agent_pattern": agent_pattern,
    }

    language = text("Language:", default=settings.language, **_text_style).unsafe_ask()

    vision_llm = settings.vision_llm.model_dump() if settings.vision_llm else llm.copy()

    setup_vision = confirm(
        "Setup Vision Model?", default=False, **_text_style
    ).unsafe_ask()
    if setup_vision:
        vision_llm = configure_vision_model()

    file_name = get_or_create_settings_path()

    with open(file_name, "w") as f:
        f.write(
            yaml.dump(
                {
                    "llm": llm,
                    "vision_llm": vision_llm,
                    "language": language,
                }
            )
        )

    print(f"\nConfiguration saved to {file_name}")


def configure_vision_model():
    provider = select(
        message="Provider:",
        choices=PROVIDERS,
        default=(
            settings.vision_llm.provider
            if settings.vision_llm
            else settings.llm.provider
        ),
        **_select_style,
    ).unsafe_ask()
    if provider != "ollama":
        api_key = password(
            message="API Key:",
            default=(
                settings.vision_llm.api_key
                if settings.vision_llm
                else settings.llm.api_key
            ),
            **_text_style,
        ).unsafe_ask()
    else:
        api_key = (
            settings.vision_llm.api_key if settings.vision_llm else settings.llm.api_key
        )
    model = input_model(
        provider,
        api_key,
        settings.vision_llm.name if settings.vision_llm else settings.llm.name,
    )
    temperature = text(
        message="Temperature:",
        default=str(
            settings.vision_llm.temperature
            if settings.vision_llm
            else settings.llm.temperature
        ),
        validate=lambda x: _try_float(x),
        **_text_style,
    ).unsafe_ask()

    return {
        "provider": provider,
        "name": model,
        "api_key": api_key,
        "temperature": float(temperature),
    }


def input_model(provider: str, api_key: str, default_model: str | None = None):
    try:
        match provider:
            case "ollama":
                from ollama import list

                r = list()
                model_list = [l["name"].replace(":latest", "") for l in r["models"]]
                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case "openai":
                from openai import OpenAI

                r = OpenAI(api_key=api_key).models.list()
                model_list = [l.id for l in r.data]
                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case "google":
                from google.generativeai.client import glm
                from google.auth.api_key import Credentials

                r = glm.ModelServiceClient(
                    credentials=Credentials(api_key)
                ).list_models()
                model_list = [l.name.replace("models/", "", 1) for l in r]
                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case "anthropic":
                import requests

                r = requests.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                ).json()
                model_list = [l["id"] for l in r["data"]]

                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case "groq":
                from groq import Client

                r = Client(api_key=api_key).models.list()
                model_list = [l.id for l in r.data]
                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case "aws":
                from boto3 import client

                region, access_key, secret_key = api_key.split(" ")
                r = client(
                    "bedrock",
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                ).list_foundation_models(
                    byOutputModality="TEXT",
                )
                model_list = [l["modelId"] for l in r["modelSummaries"]]
                return select(
                    message="Model:",
                    choices=model_list,
                    default=default_model if default_model in model_list else None,
                    **_select_style,
                ).unsafe_ask()
            case _:
                raise ValueError("Invalid provider")
    except Exception:
        return text(message="Model:", **_text_style).unsafe_ask()
