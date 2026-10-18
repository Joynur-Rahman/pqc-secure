"""Performance measurement and benchmark schemas"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkRequest(BaseModel):
    """Configuration options for benchmark execution"""
    iterations: int = Field(default=10, ge=1, le=100, description="Iterations per operation")
    file_sizes_kb: List[int] = Field(default=[1, 64, 1024], description="Payload sizes in KB for symmetric testing")
    include_pqc: bool = Field(default=True, description="Include Post-Quantum algorithms (ML-KEM-768, ML-DSA-65)")
    include_classical: bool = Field(default=True, description="Include Classical algorithms (X25519, Ed25519)")


class TimingStats(BaseModel):
    """Statistical summary of execution timing samples"""
    iterations: int
    mean_ms: float
    median_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float


class SizeMetrics(BaseModel):
    """Cryptographic object size measurements in bytes"""
    public_key_bytes: Optional[int] = None
    private_key_bytes: Optional[int] = None
    ciphertext_bytes: Optional[int] = None
    signature_bytes: Optional[int] = None
    shared_secret_bytes: Optional[int] = None
    overhead_bytes: Optional[int] = None


class BenchmarkItem(BaseModel):
    """Individual benchmark operation measurement result"""
    operation: str
    algorithm: str
    mode: str  # 'pqc', 'classical', 'symmetric'
    category: str  # 'key_generation', 'key_establishment', 'signatures', 'symmetric_encryption'
    payload_size_bytes: Optional[int] = None
    timing: TimingStats
    sizes: SizeMetrics
    throughput_mb_s: Optional[float] = None


class EnvironmentMetadata(BaseModel):
    """Hardware and runtime environment context"""
    os: str
    os_release: str
    os_version: str
    architecture: str
    cpu_model: str
    cpu_cores: int
    total_memory_mb: Optional[float] = None
    total_memory_gb: Optional[float] = None
    python_version: str
    python_compiler: str
    cryptography_version: str
    pqc_backend: str
    is_native_oqs: bool
    environment_notice: str


class BenchmarkSummary(BaseModel):
    """High-level comparison summary between PQC and Classical modes"""
    pqc_total_time_ms: float
    classical_total_time_ms: float
    time_overhead_ratio: float
    pqc_public_key_bytes: int
    classical_public_key_bytes: int
    key_size_overhead_ratio: float
    pqc_signature_bytes: int
    classical_signature_bytes: int
    signature_size_overhead_ratio: float
    pqc_ciphertext_bytes: int
    classical_ciphertext_bytes: int
    ciphertext_size_overhead_ratio: float
    fastest_keygen_algorithm: str
    fastest_signing_algorithm: str


class BenchmarkResponse(BaseModel):
    """Complete performance benchmark report"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    environment: EnvironmentMetadata
    summary: BenchmarkSummary
    results: List[BenchmarkItem]

    model_config = ConfigDict(from_attributes=True)
