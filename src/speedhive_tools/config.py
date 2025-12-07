
# src/speedhive_tools/config.py
import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    base_url: str = Field(default=os.getenv("SPEEDHIVE_BASE_URL", "http://api2.mylaps.com"))
    token: str | None = Field(default=os.getenv("SPEEDHIVE_TOKEN"))
    timeout: float = Field(default=float(os.getenv("SPEEDHIVE_TIMEOUT", "20")))
