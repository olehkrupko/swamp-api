from os import getenv

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str = getenv("SQLALCHEMY_DB_URI")
    TIMEZONE_LOCAL: str = getenv("TIMEZONE_LOCAL")
    SWAMP_PARSER = getenv('SWAMP_PARSER')
    # Telegram settings
    TELEGRAM_CHATID = getenv("TELEGRAM_CHATID")
    TELEGRAM_BROADCAST = getenv("TELEGRAM_BROADCAST", False)
    TELEGRAM_BOTTOKEN = getenv("TELEGRAM_BOTTOKEN")


# import this one:
settings = Settings()
