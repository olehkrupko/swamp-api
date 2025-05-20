from os import getenv

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str = getenv("SQLALCHEMY_DB_URI")


# import this one:
settings = Settings()
