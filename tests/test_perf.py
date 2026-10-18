"""Comprehensive tests for Performance Measurement & Evaluation (Phase 8).

Covers:
- Timing statistics calculation (median, p90, p95, min, max, std dev)
- Environment metadata collection (CPU, Memory, OS, runtime, crypto backend)
- Key generation, KEM, Signatures, and AES-GCM benchmarking
- Size measurements and overhead ratios
- POST /perf/benchmark and GET /perf/benchmark endpoints
- GET /perf/latest and GET /perf/environment endpoints
- Authentication requirement and /api prefix mounting
"""
import os
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from pqc_secure.db.models import Base
from pqc_secure.services.auth import AuthService
from pqc_secure.services.perf import PerformanceService
from pqc_secure.services.crypto import CryptoService
from pqc_secure.main import app
from pqc_secure.db.session import get_db_session
from pqc_secure.api.deps import get_db


@pytest.fixture
def db_session():
    """Create isolated SQLite database session for perf testing."""
    engine = create_engine("sqlite:///test_perf.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

    try:
        if os.path.exists("test_perf.db"):
            time.sleep(0.05)
            os.remove("test_perf.db")
    except (PermissionError, OSError):
        pass


@pytest.fixture
def client(db_session):
    """Create FastAPI test client with database dependency overrides."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user(db_session):
    """Authenticated test user."""
    auth_service = AuthService()
    _, user, _ = auth_service.register_user(db_session, "perf_user@example.com", "Password123!")
    token = auth_service.generate_token(user.id)
    return user, token


class TestPerformanceService:
    """Unit tests for PerformanceService calculations and benchmarks"""

    def test_calculate_stats_normal_distribution(self):
        """Test calculation of mean, median, percentiles, and standard deviation"""
        samples = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = PerformanceService.calculate_stats(samples)
        assert stats.iterations == 5
        assert stats.min_ms == 10.0
        assert stats.max_ms == 50.0
        assert stats.mean_ms == 30.0
        assert stats.median_ms == 30.0
        assert stats.p90_ms == 50.0
        assert stats.std_dev_ms > 0

    def test_calculate_stats_empty(self):
        """Test calculation on empty samples list"""
        stats = PerformanceService.calculate_stats([])
        assert stats.iterations == 0
        assert stats.mean_ms == 0.0
        assert stats.median_ms == 0.0

    def test_collect_environment_metadata(self):
        """Test gathering hardware and platform environment context"""
        env = PerformanceService.collect_environment()
        assert env.os != ""
        assert env.architecture != ""
        assert env.cpu_cores >= 1
        assert env.python_version != ""
        assert env.cryptography_version != ""
        assert "environment-dependent" in env.environment_notice.lower()

    def test_benchmark_key_generation(self):
        """Test keypair generation benchmark items for PQC and Classical"""
        items = PerformanceService.benchmark_key_generation(iterations=2)
        assert len(items) == 4
        ops = {i.operation for i in items}
        assert "Key Generation (KEM)" in ops
        assert "Key Generation (DSA)" in ops
        assert "Key Generation (ECDH)" in ops
        assert "Key Generation (EdDSA)" in ops

        # Check size metrics
        kem_item = next(i for i in items if i.algorithm == CryptoService.ALG_ML_KEM_768)
        assert kem_item.sizes.public_key_bytes == CryptoService.ML_KEM_768_PUBLIC_KEY_SIZE
        assert kem_item.sizes.private_key_bytes == CryptoService.ML_KEM_768_PRIVATE_KEY_SIZE

    def test_benchmark_key_establishment(self):
        """Test encapsulation and key agreement benchmarks"""
        items = PerformanceService.benchmark_key_establishment(iterations=2)
        assert len(items) == 3
        ops = {i.operation for i in items}
        assert "Encapsulation" in ops
        assert "Decapsulation" in ops
        assert "Key Agreement (ECDH)" in ops

        encap_item = next(i for i in items if i.operation == "Encapsulation")
        assert encap_item.sizes.ciphertext_bytes == CryptoService.ML_KEM_768_CIPHERTEXT_SIZE
        assert encap_item.sizes.shared_secret_bytes == 32

    def test_benchmark_signatures(self):
        """Test signing and verification benchmarks"""
        items = PerformanceService.benchmark_signatures(iterations=2)
        assert len(items) == 4
        dsa_sign = next(i for i in items if i.algorithm == CryptoService.ALG_ML_DSA_65 and i.operation == "Signing")
        assert dsa_sign.sizes.signature_bytes == CryptoService.ML_DSA_65_SIGNATURE_SIZE
        ed_sign = next(i for i in items if i.algorithm == CryptoService.ALG_ED25519 and i.operation == "Signing")
        assert ed_sign.sizes.signature_bytes == CryptoService.ED25519_SIGNATURE_SIZE

    def test_benchmark_symmetric(self):
        """Test symmetric encryption and decryption throughput and overhead"""
        items = PerformanceService.benchmark_symmetric(iterations=2, file_sizes_kb=[1, 16])
        assert len(items) == 4
        enc_1k = next(i for i in items if i.operation == "Encryption (1 KB)")
        assert enc_1k.sizes.overhead_bytes == 28  # 12 nonce + 16 tag
        assert enc_1k.throughput_mb_s is not None

    def test_run_full_benchmark_summary(self):
        """Test complete benchmark execution and summary overhead ratios"""
        resp = PerformanceService.run_benchmark(iterations=2, file_sizes_kb=[1])
        assert resp.id != ""
        assert len(resp.results) > 0
        summary = resp.summary
        assert summary.pqc_total_time_ms > 0
        assert summary.classical_total_time_ms > 0
        assert summary.key_size_overhead_ratio > 1.0
        assert summary.signature_size_overhead_ratio > 1.0


class TestPerformanceAPI:
    """Integration tests for /perf endpoints"""

    def test_unauthenticated_returns_401(self, client):
        """Verify endpoints require authentication"""
        assert client.post("/perf/benchmark", json={}).status_code == 401
        assert client.get("/perf/benchmark").status_code == 401
        assert client.get("/perf/latest").status_code == 401
        assert client.get("/perf/environment").status_code == 401

    def test_post_benchmark_success(self, client, auth_user):
        """POST /perf/benchmark executes and returns full report"""
        _, token = auth_user
        res = client.post(
            "/perf/benchmark",
            json={"iterations": 2, "file_sizes_kb": [1]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "environment" in data
        assert "summary" in data
        assert "results" in data
        assert len(data["results"]) > 0

    def test_get_benchmark_query_params(self, client, auth_user):
        """GET /perf/benchmark executes with query parameters"""
        _, token = auth_user
        res = client.get(
            "/perf/benchmark?iterations=2&file_sizes_kb=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["results"]) > 0

    def test_get_latest_benchmark(self, client, auth_user):
        """GET /perf/latest retrieves cached or fast default benchmark"""
        _, token = auth_user
        res = client.get(
            "/perf/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data

    def test_get_environment_info(self, client, auth_user):
        """GET /perf/environment returns hardware metadata and notice"""
        _, token = auth_user
        res = client.get(
            "/perf/environment",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "cpu_cores" in data
        assert "environment_notice" in data

    def test_api_prefix_mounting(self, client, auth_user):
        """Verify endpoint is mounted at /api/perf as well"""
        _, token = auth_user
        res = client.get(
            "/api/perf/environment",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert "os" in res.json()
