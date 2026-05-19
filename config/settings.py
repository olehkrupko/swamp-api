"""Application settings and configuration management.

Loads environment variables and provides a centralized Settings class
for database, timezone, Telegram, and API configuration.
"""

from os import getenv

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables.

    Attributes:
        SQLALCHEMY_DATABASE_URI: PostgreSQL database connection URI.
        TIMEZONE_LOCAL: Local timezone for the application (e.g., 'Europe/Kyiv').
        SWAMP_PARSER: URL of the swamp-parser service for parsing feeds.
        TELEGRAM_CHATID: Telegram chat ID for sending messages.
        TELEGRAM_BROADCAST: Whether to broadcast updates to Telegram.
        TELEGRAM_BOTTOKEN: Telegram bot authentication token.
    """
    SQLALCHEMY_DATABASE_URI: str = getenv("SQLALCHEMY_DB_URI")
    TIMEZONE_LOCAL: str = getenv("TIMEZONE_LOCAL")
    SWAMP_PARSER: str = getenv("SWAMP_PARSER")
    # Telegram settings
    TELEGRAM_CHATID: int = getenv("TELEGRAM_CHATID")
    TELEGRAM_BROADCAST: bool = getenv("TELEGRAM_BROADCAST", False)
    TELEGRAM_BOTTOKEN: str = getenv("TELEGRAM_BOTTOKEN")


# import this one:
# Global settings instance to be imported throughout the application
settings = Settings()
