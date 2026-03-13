"""Service metadata models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class Datastore(BaseModel):
    """Datastore infrastructure component."""
    type: str = Field(..., description="Datastore type (e.g., postgresql, mysql, mongodb)")
    name: str = Field(..., description="Datastore instance name")
    availability_slo: float = Field(..., ge=0, le=100, description="Datastore availability SLO percentage")
    latency_p95_ms: float = Field(..., gt=0, description="Datastore p95 latency in milliseconds")


class Cache(BaseModel):
    """Cache infrastructure component."""
    type: str = Field(..., description="Cache type (e.g., redis, memcached)")
    name: str = Field(..., description="Cache instance name")
    hit_rate: float = Field(..., ge=0, le=1, description="Cache hit rate (0-1)")


class MessageQueue(BaseModel):
    """Message queue infrastructure component."""
    type: str = Field(..., description="Message queue type (e.g., kafka, rabbitmq, sqs)")
    name: str = Field(..., description="Message queue instance name")


class Infrastructure(BaseModel):
    """Infrastructure components used by a service."""
    datastores: List[Datastore] = Field(default_factory=list, description="List of datastores")
    caches: List[Cache] = Field(default_factory=list, description="List of caches")
    message_queues: List[MessageQueue] = Field(default_factory=list, description="List of message queues")


class CurrentSLO(BaseModel):
    """Current SLO targets for a service."""
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


class ServiceMetadata(BaseModel):
    """Service metadata and configuration."""
    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Human-readable service name")
    service_type: str = Field(..., description="Service type (e.g., api, database, message_queue)")
    team: str = Field(..., description="Owning team name")
    tenant_id: str = Field(..., description="Tenant identifier for multi-tenancy")
    region: str = Field(..., description="Primary region (e.g., us-east-1)")
    created_at: datetime = Field(..., description="Service creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    infrastructure: Infrastructure = Field(default_factory=Infrastructure, description="Infrastructure components")
    current_slo: Optional[CurrentSLO] = Field(None, description="Current SLO targets")
