from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    storage_dir: Path = Path("./storage")
    weights_dir: Path = Path("./weights")
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.storage_dir / "processed"

    @property
    def db_path(self) -> Path:
        return self.storage_dir / "sessions.db"


settings = Settings()
