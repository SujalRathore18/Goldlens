from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class QuoteRequest(BaseModel):
    spot_inr: float = Field(gt=0)
    weight_grams: float = Field(gt=0)
    fineness: int = Field(ge=1, le=1000)


class QuoteResponse(BaseModel):
    inr_per_fine_gram: float


class AlertResponse(BaseModel):
    state: Literal["alert", "no_signal"]
    reason_code: str
    symbol: str
    date: date
    pair: str


class LifecycleRow(BaseModel):
    symbol: str
    expiry_date: date
    listing_date: date | None
    first_liquid_date: date | None
    peak_oi_date: date | None
    tender_start: date | None
    last_trade_date: date | None


class UploadValidationSummary(BaseModel):
    status: Literal["valid", "invalid"]
    row_count: int
    symbol_count: int
    date_range: dict[str, str | None]
    symbols: list[str]
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DatasetRecord(BaseModel):
    dataset_id: str
    filename: str
    validation: UploadValidationSummary
    storage_path: str


class AnalysisRequest(BaseModel):
    dataset_id: str = Field(min_length=1)
    pair: str = Field(min_length=1)
    analysis_date: str = Field(min_length=1)
    scenario: str = "base"


class AnalysisGate(BaseModel):
    code: str
    passed: bool
    detail: str


class AnalysisResponse(BaseModel):
    run_id: str
    status: str
    verdict: str
    reason_code: str | None = None
    pair: str
    dataset_id: str
    analysis_date: str
    basis: float | None = None
    cost_floor: float | None = None
    net_expected: float | None = None
    evidence: int = 0
    gates: list[AnalysisGate] = Field(default_factory=list)
    manifest: dict[str, object]


class MunimjiRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    language: Literal["en", "hi"] = "en"
    context: dict[str, object] = Field(default_factory=dict)


class MunimjiResponse(BaseModel):
    reply: str
    language: Literal["en", "hi"]
    provider: str
    source: str

