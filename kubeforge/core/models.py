from typing import Literal
from pydantic import BaseModel, Field


class ClusterConfig(BaseModel):
    name: str = Field(min_length=1)
    provider: Literal["local", "vps", "aws"]
    workers: int = Field(ge=0)
