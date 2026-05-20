from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SteamGame:
    id: UUID
    appid: int
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass
class SteamGameCreate:
    appid: int
    name: str
