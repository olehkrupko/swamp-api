from os import getenv

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLALCHEMY_TRACK_MODIFICATIONS: bool = True
    SQLALCHEMY_DATABASE_URI: str = getenv("SQLALCHEMY_DB_URI")
    # SQLALCHEMY_ECHO = True
    # SCHEDULER_API_ENABLED = True


# import this one:
settings = Settings()
