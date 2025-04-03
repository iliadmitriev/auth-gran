from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "JWT Auth API"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
