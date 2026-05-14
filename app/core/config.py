from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "sunshine-backend"
    APP_ENV: str = "local"

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "sunshine"
    DATABASE_USER: str = "sunshine"
    DATABASE_PASSWORD: str = "change-me-local-only"
    DATABASE_URL: str = ""

    UPLOAD_DIR: str = "data/uploads"
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB

    PLANT_ID_API_KEY: str = ""
    PLANT_ID_API_URL: str = "https://plant.id/api/v3"
    PLANT_ID_TIMEOUT_SECONDS: float = 10.0

    SPECIES_CLASSIFIER_PROVIDER: str = "mock"

    PLANT_KNOWLEDGE_EXCEL_PATH: str = "data/전체식물_분류정보_v1_updated_7_2.xlsx"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return self


settings = Settings()
