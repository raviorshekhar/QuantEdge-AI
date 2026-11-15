
from enum import Enum

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):

    app_name: str = "QuantEdge AI"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env == Environment.PRODUCTION and self.debug:
            raise ValueError("DEBUG must be False in production")

        return self


settings = Settings()
