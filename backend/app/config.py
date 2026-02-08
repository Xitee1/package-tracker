from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tracker:tracker@db:5432/tracker"
    secret_key: str = "change-me-in-production"
    encryption_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    model_config = {"env_prefix": "PT_"}


settings = Settings()
