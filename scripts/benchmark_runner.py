#!/usr/bin/env python3
"""Benchmark Runner for PQC-Secure: Post-Quantum vs. Classical Comparative Analysis.

Benchmarks:
1. Key Generation: ML-KEM-768 vs X25519 & ML-DSA-65 vs Ed25519
2. Key Establishment: ML-KEM Encapsulation/Decapsulation vs X25519 ECDH Key Agreement
3. Digital Signatures: ML-DSA-65 Signing/Verification vs Ed25519 Signing/Verification
4. Symmetric Throughput: AES-256-GCM 1MB encryption/decryption
5. Size Overhead: Public keys, private keys, ciphertexts, and signatures comparison.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from typing import Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pqc_secure.services.crypto import CryptoService
from pqc_secure.services.perf import PerformanceService

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def run_benchmarks(iterations: int = 50, output_json: bool = False):
    print("=" * 80)
    print(f" PQC-SECURE BENCHMARK SUITE: PQC vs. CLASSICAL (N={iterations} iterations)")
    print("=" * 80)
    print(f"Environment: Python {platform.python_version()} on {platform.system()} {platform.machine()}")
    print(f"Native liboqs Available: {CryptoService.is_oqs_available()}")
    print("-" * 80)

    # 1. Key Generation Benchmark
    print("Executing Key Generation benchmarks...")
    kem_keygen_times = []
    x25519_keygen_times = []
    dsa_keygen_times = []
    ed25519_keygen_times = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        k_pub, k_priv = CryptoService.generate_keypair_kem()
        kem_keygen_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        x_pub, x_priv = CryptoService.generate_keypair_x25519()
        x25519_keygen_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        s_pub, s_priv = CryptoService.generate_keypair_sig()
        dsa_keygen_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        ed_pub, ed_priv = CryptoService.generate_keypair_ed25519()
        ed25519_keygen_times.append((time.perf_counter() - t0) * 1000)

    # 2. Key Establishment / Encapsulation Benchmark
    print("Executing Key Establishment & Encapsulation benchmarks...")
    kem_encap_times = []
    kem_decap_times = []
    x25519_agree_times = []

    for _ in range(iterations):
        # KEM
        t0 = time.perf_counter()
        ct, ss_enc = CryptoService.encapsulate_kem(k_pub)
        kem_encap_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        ss_dec = CryptoService.decapsulate_kem(ct, k_priv)
        kem_decap_times.append((time.perf_counter() - t0) * 1000)

        # X25519
        t0 = time.perf_counter()
        ephem_pub, ephem_priv = CryptoService.generate_keypair_x25519()
        shared = CryptoService.agree_x25519(ephem_priv, x_pub)
        x25519_agree_times.append((time.perf_counter() - t0) * 1000)

    # 3. Signature & Verification Benchmark
    print("Executing Signature & Verification benchmarks...")
    test_message = b"NIST FIPS post-quantum digital signature benchmark payload"
    dsa_sign_times = []
    dsa_verify_times = []
    ed_sign_times = []
    ed_verify_times = []

    for _ in range(iterations):
        # ML-DSA-65
        t0 = time.perf_counter()
        dsa_sig = CryptoService.sign_dsa(test_message, s_priv)
        dsa_sign_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        CryptoService.verify_dsa(test_message, dsa_sig, s_pub)
        dsa_verify_times.append((time.perf_counter() - t0) * 1000)

        # Ed25519
        t0 = time.perf_counter()
        ed_sig = CryptoService.sign_ed25519(test_message, ed_priv)
        ed_sign_times.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        CryptoService.verify_ed25519(test_message, ed_sig, ed_pub)
        ed_verify_times.append((time.perf_counter() - t0) * 1000)

    # Helpers
    def median(arr: List[float]) -> float:
        s = sorted(arr)
        return s[len(s) // 2]

    # Report results
    results = {
        "environment": {
            "os": platform.system(),
            "cpu": platform.processor() or platform.machine(),
            "python": platform.python_version(),
            "liboqs_available": CryptoService.is_oqs_available(),
        },
        "key_generation_ms": {
            "ml_kem_768_median": round(median(kem_keygen_times), 3),
            "x25519_median": round(median(x25519_keygen_times), 3),
            "ml_dsa_65_median": round(median(dsa_keygen_times), 3),
            "ed25519_median": round(median(ed25519_keygen_times), 3),
        },
        "key_establishment_ms": {
            "ml_kem_768_encap_median": round(median(kem_encap_times), 3),
            "ml_kem_768_decap_median": round(median(kem_decap_times), 3),
            "x25519_agree_median": round(median(x25519_agree_times), 3),
        },
        "digital_signatures_ms": {
            "ml_dsa_65_sign_median": round(median(dsa_sign_times), 3),
            "ml_dsa_65_verify_median": round(median(dsa_verify_times), 3),
            "ed25519_sign_median": round(median(ed_sign_times), 3),
            "ed25519_verify_median": round(median(ed_verify_times), 3),
        },
        "sizes_bytes": {
            "ml_kem_768": {
                "public_key": len(k_pub),
                "private_key": len(k_priv),
                "ciphertext": len(ct),
            },
            "x25519": {
                "public_key": len(x_pub),
                "private_key": len(x_priv),
                "ciphertext": len(x_pub),
            },
            "ml_dsa_65": {
                "public_key": len(s_pub),
                "private_key": len(s_priv),
                "signature": len(dsa_sig),
            },
            "ed25519": {
                "public_key": len(ed_pub),
                "private_key": len(ed_priv),
                "signature": len(ed_sig),
            },
        },
    }

    if output_json:
        print(json.dumps(results, indent=2))
        return

    # Print Table
    print("\n" + "=" * 80)
    print(" TIMING COMPARISON (Median in milliseconds)")
    print("=" * 80)
    print(f"{'Operation':<35} | {'PQC (ML-KEM / ML-DSA)':<20} | {'Classical (X25519 / Ed25519)':<20}")
    print("-" * 80)
    print(f"{'KEM/Agreement Keygen':<35} | {results['key_generation_ms']['ml_kem_768_median']:>15.3f} ms | {results['key_generation_ms']['x25519_median']:>22.3f} ms")
    print(f"{'Signature Keygen':<35} | {results['key_generation_ms']['ml_dsa_65_median']:>15.3f} ms | {results['key_generation_ms']['ed25519_median']:>22.3f} ms")
    print(f"{'Encapsulation / Agreement':<35} | {results['key_establishment_ms']['ml_kem_768_encap_median']:>15.3f} ms | {results['key_establishment_ms']['x25519_agree_median']:>22.3f} ms")
    print(f"{'Decapsulation':<35} | {results['key_establishment_ms']['ml_kem_768_decap_median']:>15.3f} ms | {'N/A (Symmetric)':>24}")
    print(f"{'Signing':<35} | {results['digital_signatures_ms']['ml_dsa_65_sign_median']:>15.3f} ms | {results['digital_signatures_ms']['ed25519_sign_median']:>22.3f} ms")
    print(f"{'Verification':<35} | {results['digital_signatures_ms']['ml_dsa_65_verify_median']:>15.3f} ms | {results['digital_signatures_ms']['ed25519_verify_median']:>22.3f} ms")

    print("\n" + "=" * 80)
    print(" ARTIFACT SIZE COMPARISON (Bytes)")
    print("=" * 80)
    print(f"{'Artifact':<25} | {'PQC':<15} | {'Classical':<15} | {'Ratio (PQC / Classical)':<15}")
    print("-" * 80)
    kem_pub_pqc = results["sizes_bytes"]["ml_kem_768"]["public_key"]
    kem_pub_cla = results["sizes_bytes"]["x25519"]["public_key"]
    print(f"{'KEM/Agreement PubKey':<25} | {kem_pub_pqc:>12} B | {kem_pub_cla:>12} B | {kem_pub_pqc / kem_pub_cla:>15.1f}x")

    dsa_pub_pqc = results["sizes_bytes"]["ml_dsa_65"]["public_key"]
    dsa_pub_cla = results["sizes_bytes"]["ed25519"]["public_key"]
    print(f"{'Signature PubKey':<25} | {dsa_pub_pqc:>12} B | {dsa_pub_cla:>12} B | {dsa_pub_pqc / dsa_pub_cla:>15.1f}x")

    kem_ct_pqc = results["sizes_bytes"]["ml_kem_768"]["ciphertext"]
    kem_ct_cla = results["sizes_bytes"]["x25519"]["ciphertext"]
    print(f"{'Ciphertext / Exchange':<25} | {kem_ct_pqc:>12} B | {kem_ct_cla:>12} B | {kem_ct_pqc / kem_ct_cla:>15.1f}x")

    sig_pqc = results["sizes_bytes"]["ml_dsa_65"]["signature"]
    sig_cla = results["sizes_bytes"]["ed25519"]["signature"]
    print(f"{'Digital Signature':<25} | {sig_pqc:>12} B | {sig_cla:>12} B | {sig_pqc / sig_cla:>15.1f}x")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PQC vs Classical Benchmark Runner")
    parser.add_argument("-n", "--iterations", type=int, default=30, help="Number of benchmark iterations")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()
    run_benchmarks(iterations=args.iterations, output_json=args.json)
