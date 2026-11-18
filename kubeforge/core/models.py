from typing import Literal
from pydantic import BaseModel, Field


class ClusterConfig(BaseModel):
    name: str = Field(min_length=1)
    provider: Literal["local", "vps", "aws"]
    workers: int = Field(ge=0)

class VPSHost(BaseModel):
    host: str = Field(min_length=1)
    user: str = Field(min_length=1)
    port: int = Field(default=22, ge=1, le=65535)


class VPSConfig(BaseModel):
    control_plane: VPSHost
    workers: list[VPSHost] = Field(default_factory=list)
