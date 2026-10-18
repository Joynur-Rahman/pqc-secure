"""Performance measurement and benchmark service for Post-Quantum & Classical Cryptography.

Measures:
- Key generation timing and sizes (ML-KEM-768, ML-DSA-65, X25519, Ed25519)
- Key establishment / encapsulation timing and sizes (ML-KEM-768, X25519)
- Digital signature generation and verification timing and sizes (ML-DSA-65, Ed25519)
- Symmetric encryption and decryption throughput and overhead (AES-256-GCM)
- Environment context metadata and statistical distributions (median, p90, p95, p99, min, max, std dev)
"""
from __future__ import annotations

import math
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import cryptography

from pqc_secure.schemas.perf import (
    BenchmarkItem,
    BenchmarkRequest,
    BenchmarkResponse,
    BenchmarkSummary,
    EnvironmentMetadata,
    SizeMetrics,
    TimingStats,
)
from pqc_secure.services.crypto import CryptoService


class PerformanceService:
    """Enterprise performance measurement service evaluating PQC and Classical cryptosystems."""

    _cached_latest: Optional[BenchmarkResponse] = None

    @classmethod
    def get_total_memory_bytes(cls) -> Optional[int]:
        """Detect system total physical RAM in bytes across platforms."""
        try:
            import psutil
            return psutil.virtual_memory().total
        except Exception:
            pass

        # Windows fallback via kernel32 GlobalMemoryStatusEx
        if sys.platform == "win32":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    return int(stat.ullTotalPhys)
            except Exception:
                pass

        # Linux fallback via /proc/meminfo
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            parts = line.split()
                            return int(parts[1]) * 1024
        except Exception:
            pass

        return None

    @classmethod
    def collect_environment(cls) -> EnvironmentMetadata:
        """Gather detailed hardware, OS, and cryptographic runtime metadata."""
        total_bytes = cls.get_total_memory_bytes()
        total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes else None
        total_gb = round(total_bytes / (1024 * 1024 * 1024), 2) if total_bytes else None

        cpu_info = platform.processor() or "Unknown CPU"
        cores = os.cpu_count() or 1

        is_oqs = CryptoService.is_oqs_available()
        backend_name = "liboqs-native (C extensions)" if is_oqs else "NIST FIPS standards-compliant emulation fallback"

        notice = (
            "Measurements are environment-dependent (hardware, CPU frequency scaling, "
            "background load, virtualization) and representative of the current host."
        )

        return EnvironmentMetadata(
            os=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            architecture=platform.machine(),
            cpu_model=cpu_info,
            cpu_cores=cores,
            total_memory_mb=total_mb,
            total_memory_gb=total_gb,
            python_version=platform.python_version(),
            python_compiler=platform.python_compiler(),
            cryptography_version=cryptography.__version__,
            pqc_backend=backend_name,
            is_native_oqs=is_oqs,
            environment_notice=notice,
        )

    @classmethod
    def calculate_stats(cls, samples_ms: List[float]) -> TimingStats:
        """Calculate statistical distribution for a series of execution times."""
        n = len(samples_ms)
        if n == 0:
            return TimingStats(
                iterations=0,
                mean_ms=0.0,
                median_ms=0.0,
                p90_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                min_ms=0.0,
                max_ms=0.0,
                std_dev_ms=0.0,
            )

        sorted_samples = sorted(samples_ms)
        mean_val = sum(samples_ms) / n

        # Median (50th percentile)
        if n % 2 == 1:
            median_val = sorted_samples[n // 2]
        else:
            median_val = (sorted_samples[n // 2 - 1] + sorted_samples[n // 2]) / 2.0

        def percentile(pct: float) -> float:
            idx = max(0, min(int(math.ceil(pct * n)) - 1, n - 1))
            return sorted_samples[idx]

        p90_val = percentile(0.90)
        p95_val = percentile(0.95)
        p99_val = percentile(0.99)
        min_val = sorted_samples[0]
        max_val = sorted_samples[-1]

        variance = sum((x - mean_val) ** 2 for x in samples_ms) / (n - 1 if n > 1 else 1)
        std_dev = math.sqrt(variance)

        return TimingStats(
            iterations=n,
            mean_ms=round(mean_val, 3),
            median_ms=round(median_val, 3),
            p90_ms=round(p90_val, 3),
            p95_ms=round(p95_val, 3),
            p99_ms=round(p99_val, 3),
            min_ms=round(min_val, 3),
            max_ms=round(max_val, 3),
            std_dev_ms=round(std_dev, 3),
        )

    @classmethod
    def measure_operation(
        cls,
        func: Callable[[], Any],
        iterations: int = 10,
        warmup: int = 2,
    ) -> Tuple[TimingStats, Any]:
        """Execute a benchmarked operation with warm-up and high-precision timing."""
        # Warmup executions to prime instruction caches
        last_result = None
        for _ in range(max(1, warmup)):
            last_result = func()

        samples_ms = []
        for _ in range(iterations):
            start_ns = time.perf_counter_ns()
            last_result = func()
            end_ns = time.perf_counter_ns()
            elapsed_ms = (end_ns - start_ns) / 1_000_000.0
            samples_ms.append(elapsed_ms)

        stats = cls.calculate_stats(samples_ms)
        return stats, last_result

    @classmethod
    def benchmark_key_generation(
        cls,
        iterations: int = 10,
        include_pqc: bool = True,
        include_classical: bool = True,
    ) -> List[BenchmarkItem]:
        """Benchmark keypair generation for PQC and Classical algorithms."""
        items: List[BenchmarkItem] = []

        if include_pqc:
            # 1. ML-KEM-768 Key Generation
            stats, (kem_pub, kem_priv) = cls.measure_operation(
                CryptoService.generate_keypair_kem, iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Key Generation (KEM)",
                    algorithm=CryptoService.ALG_ML_KEM_768,
                    mode="pqc",
                    category="key_generation",
                    timing=stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(kem_pub),
                        private_key_bytes=len(kem_priv),
                    ),
                )
            )

            # 2. ML-DSA-65 Key Generation
            stats, (dsa_pub, dsa_priv) = cls.measure_operation(
                CryptoService.generate_keypair_sig, iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Key Generation (DSA)",
                    algorithm=CryptoService.ALG_ML_DSA_65,
                    mode="pqc",
                    category="key_generation",
                    timing=stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(dsa_pub),
                        private_key_bytes=len(dsa_priv),
                    ),
                )
            )

        if include_classical:
            # 3. X25519 Key Generation
            stats, (x_pub, x_priv) = cls.measure_operation(
                CryptoService.generate_keypair_x25519, iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Key Generation (ECDH)",
                    algorithm=CryptoService.ALG_X25519,
                    mode="classical",
                    category="key_generation",
                    timing=stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(x_pub),
                        private_key_bytes=len(x_priv),
                    ),
                )
            )

            # 4. Ed25519 Key Generation
            stats, (ed_pub, ed_priv) = cls.measure_operation(
                CryptoService.generate_keypair_ed25519, iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Key Generation (EdDSA)",
                    algorithm=CryptoService.ALG_ED25519,
                    mode="classical",
                    category="key_generation",
                    timing=stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(ed_pub),
                        private_key_bytes=len(ed_priv),
                    ),
                )
            )

        return items

    @classmethod
    def benchmark_key_establishment(
        cls,
        iterations: int = 10,
        include_pqc: bool = True,
        include_classical: bool = True,
    ) -> List[BenchmarkItem]:
        """Benchmark encapsulation/decapsulation vs Diffie-Hellman key agreement."""
        items: List[BenchmarkItem] = []

        if include_pqc:
            kem_pub, kem_priv = CryptoService.generate_keypair_kem()

            # Encapsulation
            encap_stats, (ct, ss) = cls.measure_operation(
                lambda: CryptoService.encapsulate_kem(kem_pub), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Encapsulation",
                    algorithm=CryptoService.ALG_ML_KEM_768,
                    mode="pqc",
                    category="key_establishment",
                    timing=encap_stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(kem_pub),
                        ciphertext_bytes=len(ct),
                        shared_secret_bytes=len(ss),
                    ),
                )
            )

            # Decapsulation
            decap_stats, ss_out = cls.measure_operation(
                lambda: CryptoService.decapsulate_kem(ct, kem_priv), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Decapsulation",
                    algorithm=CryptoService.ALG_ML_KEM_768,
                    mode="pqc",
                    category="key_establishment",
                    timing=decap_stats,
                    sizes=SizeMetrics(
                        ciphertext_bytes=len(ct),
                        shared_secret_bytes=len(ss_out),
                    ),
                )
            )

        if include_classical:
            x_pub1, x_priv1 = CryptoService.generate_keypair_x25519()
            x_pub2, x_priv2 = CryptoService.generate_keypair_x25519()

            agree_stats, ss = cls.measure_operation(
                lambda: CryptoService.agree_x25519(x_priv1, x_pub2), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Key Agreement (ECDH)",
                    algorithm=CryptoService.ALG_X25519,
                    mode="classical",
                    category="key_establishment",
                    timing=agree_stats,
                    sizes=SizeMetrics(
                        public_key_bytes=len(x_pub1),
                        shared_secret_bytes=len(ss),
                    ),
                )
            )

        return items

    @classmethod
    def benchmark_signatures(
        cls,
        iterations: int = 10,
        include_pqc: bool = True,
        include_classical: bool = True,
    ) -> List[BenchmarkItem]:
        """Benchmark signing and verification for ML-DSA-65 vs Ed25519."""
        items: List[BenchmarkItem] = []
        test_message = b"PQC-SECURE: Benchmark canonical package manifest payload to evaluate digital signatures."

        if include_pqc:
            dsa_pub, dsa_priv = CryptoService.generate_keypair_sig()

            # Signing
            sign_stats, sig = cls.measure_operation(
                lambda: CryptoService.sign_dsa(test_message, dsa_priv), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Signing",
                    algorithm=CryptoService.ALG_ML_DSA_65,
                    mode="pqc",
                    category="signatures",
                    payload_size_bytes=len(test_message),
                    timing=sign_stats,
                    sizes=SizeMetrics(
                        signature_bytes=len(sig),
                        public_key_bytes=len(dsa_pub),
                    ),
                )
            )

            # Verification
            verify_stats, is_valid = cls.measure_operation(
                lambda: CryptoService.verify_dsa(test_message, sig, dsa_pub), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Verification",
                    algorithm=CryptoService.ALG_ML_DSA_65,
                    mode="pqc",
                    category="signatures",
                    payload_size_bytes=len(test_message),
                    timing=verify_stats,
                    sizes=SizeMetrics(
                        signature_bytes=len(sig),
                        public_key_bytes=len(dsa_pub),
                    ),
                )
            )

        if include_classical:
            ed_pub, ed_priv = CryptoService.generate_keypair_ed25519()

            # Signing
            sign_stats, sig = cls.measure_operation(
                lambda: CryptoService.sign_ed25519(test_message, ed_priv), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Signing",
                    algorithm=CryptoService.ALG_ED25519,
                    mode="classical",
                    category="signatures",
                    payload_size_bytes=len(test_message),
                    timing=sign_stats,
                    sizes=SizeMetrics(
                        signature_bytes=len(sig),
                        public_key_bytes=len(ed_pub),
                    ),
                )
            )

            # Verification
            verify_stats, is_valid = cls.measure_operation(
                lambda: CryptoService.verify_ed25519(test_message, sig, ed_pub), iterations=iterations
            )
            items.append(
                BenchmarkItem(
                    operation="Verification",
                    algorithm=CryptoService.ALG_ED25519,
                    mode="classical",
                    category="signatures",
                    payload_size_bytes=len(test_message),
                    timing=verify_stats,
                    sizes=SizeMetrics(
                        signature_bytes=len(sig),
                        public_key_bytes=len(ed_pub),
                    ),
                )
            )

        return items

    @classmethod
    def benchmark_symmetric(
        cls,
        iterations: int = 10,
        file_sizes_kb: Optional[List[int]] = None,
    ) -> List[BenchmarkItem]:
        """Benchmark AES-256-GCM authenticated encryption & decryption over configured sizes."""
        import secrets
        sizes_kb = file_sizes_kb or [1, 64, 1024]
        items: List[BenchmarkItem] = []
        aes_key = secrets.token_bytes(CryptoService.AES_256_KEY_SIZE)
        aad = b"PQC-SECURE-BENCHMARK-AAD"

        for kb in sizes_kb:
            payload_bytes = kb * 1024
            # Deterministic test pattern
            plaintext = b"PQC-BENCH-DATA-BLOCK" * (payload_bytes // 20) + b"A" * (payload_bytes % 20)

            # Encryption: returns (nonce, ciphertext)
            enc_stats, (nonce, ciphertext) = cls.measure_operation(
                lambda: CryptoService.encrypt_aes_gcm(aes_key, plaintext, associated_data=aad),
                iterations=iterations,
            )

            # Throughput in MB/s
            throughput_mb_s = (
                round((payload_bytes / (1024 * 1024)) / (enc_stats.median_ms / 1000.0), 2)
                if enc_stats.median_ms > 0
                else 0.0
            )

            items.append(
                BenchmarkItem(
                    operation=f"Encryption ({kb} KB)",
                    algorithm="AES-256-GCM",
                    mode="symmetric",
                    category="symmetric_encryption",
                    payload_size_bytes=payload_bytes,
                    timing=enc_stats,
                    sizes=SizeMetrics(
                        ciphertext_bytes=len(ciphertext),
                        overhead_bytes=len(nonce) + (len(ciphertext) - payload_bytes),
                    ),
                    throughput_mb_s=throughput_mb_s,
                )
            )

            # Decryption
            dec_stats, decrypted = cls.measure_operation(
                lambda: CryptoService.decrypt_aes_gcm(aes_key, nonce, ciphertext, associated_data=aad),
                iterations=iterations,
            )

            dec_throughput = (
                round((payload_bytes / (1024 * 1024)) / (dec_stats.median_ms / 1000.0), 2)
                if dec_stats.median_ms > 0
                else 0.0
            )

            items.append(
                BenchmarkItem(
                    operation=f"Decryption ({kb} KB)",
                    algorithm="AES-256-GCM",
                    mode="symmetric",
                    category="symmetric_encryption",
                    payload_size_bytes=payload_bytes,
                    timing=dec_stats,
                    sizes=SizeMetrics(
                        ciphertext_bytes=len(ciphertext),
                        overhead_bytes=len(nonce) + (len(ciphertext) - payload_bytes),
                    ),
                    throughput_mb_s=dec_throughput,
                )
            )

        return items

    @classmethod
    def run_benchmark(
        cls,
        iterations: int = 10,
        file_sizes_kb: Optional[List[int]] = None,
        include_pqc: bool = True,
        include_classical: bool = True,
    ) -> BenchmarkResponse:
        """Run complete benchmark suite comparing Post-Quantum and Classical cryptography."""
        env_meta = cls.collect_environment()

        results: List[BenchmarkItem] = []
        results.extend(cls.benchmark_key_generation(iterations, include_pqc, include_classical))
        results.extend(cls.benchmark_key_establishment(iterations, include_pqc, include_classical))
        results.extend(cls.benchmark_signatures(iterations, include_pqc, include_classical))
        results.extend(cls.benchmark_symmetric(iterations, file_sizes_kb))

        # Calculate high-level summary metrics
        pqc_total_ms = sum(item.timing.median_ms for item in results if item.mode == "pqc")
        classical_total_ms = sum(item.timing.median_ms for item in results if item.mode == "classical")

        time_ratio = (
            round(pqc_total_ms / classical_total_ms, 2)
            if classical_total_ms > 0
            else 1.0
        )

        pqc_pub_bytes = CryptoService.ML_KEM_768_PUBLIC_KEY_SIZE + CryptoService.ML_DSA_65_PUBLIC_KEY_SIZE
        classical_pub_bytes = CryptoService.X25519_KEY_SIZE + CryptoService.ED25519_KEY_SIZE
        key_ratio = round(pqc_pub_bytes / classical_pub_bytes, 1)

        pqc_sig_bytes = CryptoService.ML_DSA_65_SIGNATURE_SIZE
        classical_sig_bytes = CryptoService.ED25519_SIGNATURE_SIZE
        sig_ratio = round(pqc_sig_bytes / classical_sig_bytes, 1)

        pqc_ct_bytes = CryptoService.ML_KEM_768_CIPHERTEXT_SIZE
        classical_ct_bytes = CryptoService.X25519_KEY_SIZE
        ct_ratio = round(pqc_ct_bytes / classical_ct_bytes, 1)

        # Algorithm speed comparisons
        keygen_pqc = next((i for i in results if i.operation == "Key Generation (KEM)"), None)
        keygen_class = next((i for i in results if i.operation == "Key Generation (ECDH)"), None)
        fastest_keygen = (
            "X25519"
            if keygen_class and keygen_pqc and keygen_class.timing.median_ms < keygen_pqc.timing.median_ms
            else "ML-KEM-768"
        )

        sign_pqc = next((i for i in results if i.operation == "Signing" and i.mode == "pqc"), None)
        sign_class = next((i for i in results if i.operation == "Signing" and i.mode == "classical"), None)
        fastest_signing = (
            "Ed25519"
            if sign_class and sign_pqc and sign_class.timing.median_ms < sign_pqc.timing.median_ms
            else "ML-DSA-65"
        )

        summary = BenchmarkSummary(
            pqc_total_time_ms=round(pqc_total_ms, 3),
            classical_total_time_ms=round(classical_total_ms, 3),
            time_overhead_ratio=time_ratio,
            pqc_public_key_bytes=pqc_pub_bytes,
            classical_public_key_bytes=classical_pub_bytes,
            key_size_overhead_ratio=key_ratio,
            pqc_signature_bytes=pqc_sig_bytes,
            classical_signature_bytes=classical_sig_bytes,
            signature_size_overhead_ratio=sig_ratio,
            pqc_ciphertext_bytes=pqc_ct_bytes,
            classical_ciphertext_bytes=classical_ct_bytes,
            ciphertext_size_overhead_ratio=ct_ratio,
            fastest_keygen_algorithm=fastest_keygen,
            fastest_signing_algorithm=fastest_signing,
        )

        response = BenchmarkResponse(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            environment=env_meta,
            summary=summary,
            results=results,
        )

        cls._cached_latest = response
        return response

    @classmethod
    def get_latest_benchmark(cls) -> BenchmarkResponse:
        """Retrieve most recent benchmark report, generating a fast default run if None exists."""
        if cls._cached_latest is None:
            cls._cached_latest = cls.run_benchmark(iterations=5, file_sizes_kb=[1, 64, 1024])
        return cls._cached_latest
