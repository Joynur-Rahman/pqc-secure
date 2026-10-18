"""Performance evaluation API endpoints."""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from pqc_secure.api.deps import get_current_active_user
from pqc_secure.db.models import User
from pqc_secure.schemas.perf import (
    BenchmarkRequest,
    BenchmarkResponse,
    EnvironmentMetadata,
)
from pqc_secure.services.perf import PerformanceService

router = APIRouter(prefix="/perf", tags=["performance"])


@router.post("/benchmark", response_model=BenchmarkResponse, status_code=status.HTTP_200_OK)
async def run_benchmark(
    body: BenchmarkRequest,
    current_user: User = Depends(get_current_active_user),
) -> BenchmarkResponse:
    """
    Execute cryptographic benchmark comparing Post-Quantum and Classical suites.
    
    Measures timing distributions (median, p90, p95, min, max, mean, std_dev) and
    key/ciphertext/signature sizes for:
    - ML-KEM-768 vs X25519 (Key establishment)
    - ML-DSA-65 vs Ed25519 (Digital signatures)
    - AES-256-GCM authenticated encryption across requested payload sizes
    
    Includes environment context metadata and environment-dependent disclaimers.
    """
    return PerformanceService.run_benchmark(
        iterations=body.iterations,
        file_sizes_kb=body.file_sizes_kb,
        include_pqc=body.include_pqc,
        include_classical=body.include_classical,
    )


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    iterations: int = Query(10, ge=1, le=100, description="Iterations per operation"),
    file_sizes_kb: Optional[str] = Query("1,64,1024", description="Comma-separated file sizes in KB"),
    include_pqc: bool = Query(True, description="Include Post-Quantum algorithms"),
    include_classical: bool = Query(True, description="Include Classical algorithms"),
    current_user: User = Depends(get_current_active_user),
) -> BenchmarkResponse:
    """Run benchmark via GET with query parameters."""
    parsed_sizes = [int(s.strip()) for s in file_sizes_kb.split(",") if s.strip().isdigit()] if file_sizes_kb else [1, 64, 1024]
    return PerformanceService.run_benchmark(
        iterations=iterations,
        file_sizes_kb=parsed_sizes,
        include_pqc=include_pqc,
        include_classical=include_classical,
    )


@router.get("/latest", response_model=BenchmarkResponse)
async def get_latest_benchmark(
    current_user: User = Depends(get_current_active_user),
) -> BenchmarkResponse:
    """Retrieve the latest cached benchmark results without re-running."""
    return PerformanceService.get_latest_benchmark()


@router.get("/environment", response_model=EnvironmentMetadata)
async def get_environment_info(
    current_user: User = Depends(get_current_active_user),
) -> EnvironmentMetadata:
    """Retrieve host system specifications and cryptographic environment context."""
    return PerformanceService.collect_environment()
