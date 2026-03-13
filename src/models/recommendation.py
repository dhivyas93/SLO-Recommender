"""Recommendation models."""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator


class SLOTier(BaseModel):
    """SLO recommendation tier."""
    availability: float = Field(..., ge=0, le=100, description="Availability percentage")
    latency_p95_ms: float = Field(..., gt=0, description="p95 latency in milliseconds")
    latency_p99_ms: float = Field(..., gt=0, description="p99 latency in milliseconds")
    error_rate_percent: float = Field(..., ge=0, le=100, description="Error rate percentage")

    @validator("latency_p99_ms")
    def validate_latency_ordering(cls, v, values):
        """Ensure p99 >= p95."""
        if "latency_p95_ms" in values and v < values["latency_p95_ms"]:
            raise ValueError("latency_p99_ms must be >= latency_p95_ms")
        return v


class RecommendationExplanation(BaseModel):
    """Explanation for recommendation."""
    summary: str = Field(..., description="One-sentence summary")
    top_factors: List[str] = Field(..., description="Top 3 influencing factors")
    dependency_constraints: List[str] = Field(default_factory=list, description="Dependency constraints")
    infrastructure_bottlenecks: List[str] = Field(default_factory=list, description="Infrastructure bottlenecks")
    similar_services: List[str] = Field(default_factory=list, description="Similar services references")

    @validator("top_factors")
    def validate_top_factors_length(cls, v):
        """Ensure top_factors has 1-3 items."""
        if len(v) < 1 or len(v) > 3:
            raise ValueError("top_factors must contain 1-3 items")
        return v


class ConfidenceScore(BaseModel):
    """Confidence score breakdown."""
    data_completeness: float = Field(..., ge=0, le=0.3, description="Data completeness component")
    historical_stability: float = Field(..., ge=0, le=0.3, description="Historical stability component")
    dependency_clarity: float = Field(..., ge=0, le=0.2, description="Dependency clarity component")
    knowledge_base_match: float = Field(..., ge=0, le=0.2, description="Knowledge base match component")
    total: float = Field(..., ge=0, le=1, description="Total confidence score")

    @validator("total")
    def validate_total(cls, v, values):
        """Ensure total matches sum of components."""
        if all(k in values for k in ["data_completeness", "historical_stability", "dependency_clarity", "knowledge_base_match"]):
            expected = (
                values["data_completeness"] +
                values["historical_stability"] +
                values["dependency_clarity"] +
                values["knowledge_base_match"]
            )
            if abs(v - expected) > 0.01:  # Allow small floating point errors
                raise ValueError(f"Total confidence score {v} does not match sum of components {expected}")
        return v


class DataQualityInfo(BaseModel):
    """Data quality information."""
    completeness: float = Field(..., ge=0, le=1, description="Data completeness")
    staleness_hours: int = Field(..., ge=0, description="Data staleness in hours")
    quality_score: float = Field(..., ge=0, le=1, description="Overall quality score")


class Recommendation(BaseModel):
    """SLO recommendation for a service."""
    service_id: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Recommendation version")
    timestamp: datetime = Field(..., description="Recommendation timestamp")
    recommendations: Dict[str, SLOTier] = Field(
        ..., description="Recommendation tiers (aggressive, balanced, conservative)"
    )
    recommended_tier: str = Field(..., description="Recommended tier name")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence score")
    confidence_breakdown: Optional[ConfidenceScore] = Field(None, description="Confidence score breakdown")
    explanation: RecommendationExplanation = Field(..., description="Recommendation explanation")
    data_quality: DataQualityInfo = Field(..., description="Data quality information")
