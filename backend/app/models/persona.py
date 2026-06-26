from pydantic import BaseModel, Field


class Persona(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
