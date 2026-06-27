import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_upload_size_mb: int
    log_level: str


def get_settings() -> Settings:
    return Settings(
        max_upload_size_mb=int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
