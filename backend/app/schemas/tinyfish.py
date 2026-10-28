from pydantic import BaseModel, Field


class TinyFishRunRequest(BaseModel):
    url: str = Field(min_length=1)
    goal: str = Field(min_length=1)


class TinyFishRunResponse(BaseModel):
    status: str
    run_id: str | None = None
    result: object | None = None
    error: str | None = None
