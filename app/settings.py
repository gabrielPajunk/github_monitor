from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PATH: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    GITHUB_TOKEN: str

    class Config:
        env_file = "app/.env"
