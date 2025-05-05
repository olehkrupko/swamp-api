from os import getenv


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = getenv("SQLALCHEMY_DB_URI")
    # SQLALCHEMY_ECHO = True
    # SCHEDULER_API_ENABLED = True
