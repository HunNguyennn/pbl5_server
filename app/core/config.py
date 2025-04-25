import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MODEL_PATH: str = "app/models/yolov8n_dynamic.tflite"
    PREDICTION_INTERVAL: float = 1.0
    CONF_THRESHOLD: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()