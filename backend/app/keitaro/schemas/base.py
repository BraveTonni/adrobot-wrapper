"""Базовая модель DTO Admin API."""

from pydantic import BaseModel, ConfigDict


class KeitaroModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
