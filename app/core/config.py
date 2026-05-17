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

    SPECIES_CLASSIFIER_PROVIDER: str = "catalog_mock"  # catalog_mock | mock (alias) | plant_id | qwen_vl
    QWEN_VL_MODEL: str = "qwen3-vl"
    QWEN_VL_BASE_URL: str = ""
    QWEN_VL_TIMEOUT_SECONDS: float = 120.0

    PLANT_KNOWLEDGE_EXCEL_PATH: str = "data/전체식물_분류정보_v1_updated_7_2.xlsx"

    EMBEDDING_MODEL_NAME: str = "Qwen/Qwen3-Embedding-0.6B"
    EMBEDDING_VECTOR_DIM: int = 1024
    EMBEDDING_NORMALIZE: bool = True

    LLM_BACKEND: str = "mock"
    QWEN_LLM_MODEL: str = "qwen3.6"
    QWEN_LLM_BASE_URL: str = "http://localhost:8080"
    QWEN_LLM_TIMEOUT_SECONDS: float = 120.0
    QWEN_LLM_API_KEY: str = ""
    QWEN_LLM_AUTH_HEADER: str = "Authorization"
    QWEN_ENDPOINT_REGISTRY_MODE: str = "env"  # env | file | db
    QWEN_ENDPOINT_REGISTRY_FILE: str = "/app/runtime/qwen_endpoint.json"

    INTERNAL_TOKEN: str = ""

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
