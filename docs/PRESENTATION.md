# PQC-Secure: Hackathon Milestone Presentation & Architecture Overview

---

## 1. Executive Summary

**PQC-Secure** is an enterprise-grade secure file sharing and storage platform engineered to counter the imminent threat posed by quantum computers. Built upon the newly finalized **NIST FIPS 203 (ML-KEM-768)** and **NIST FIPS 204 (ML-DSA-65)** standards, PQC-Secure protects confidential organizational files from "Harvest Now, Decrypt Later" quantum surveillance while providing sub-millisecond crypto performance and active tampering defense.

---

## 2. Core Problem: The Quantum Threat Horizon

- **Harvest Now, Decrypt Later (HNDL)**: Adversaries are currently intercepting and storing encrypted communications and files. When a Cryptanalytically Relevant Quantum Computer (CRQC) emerges, Shor's algorithm will compromise all classical RSA and ECC infrastructure.
- **The Challenge**: Upgrading cryptography is difficult because post-quantum lattice keys and signatures are substantially larger than classical keys, requiring modern envelope encryption, chunked streaming, and rigorous access controls.

---

## 3. Key Technical Innovations

1. **Dual Cryptographic Architecture (PQC + Classical)**:
   - **Post-Quantum**: ML-KEM-768 key encapsulation + ML-DSA-65 canonical manifest signing.
   - **Classical Fallback**: X25519 ephemeral ECDH + Ed25519 digital signatures.
2. **Multi-Recipient Envelope Encryption**:
   - Single symmetric encryption pass of large files using AES-256-GCM and a random Content Encryption Key (CEK).
   - Independent per-recipient KEM encapsulation wrapped via HKDF-SHA-256.
3. **Multi-Layer Tampering Defense**:
   - Manifest digital signature rejection if metadata or file parameters are altered.
   - 128-bit AES-GCM authentication failure if payload ciphertext bits are flipped.
   - Context-bound Additional Authenticated Data (`PQC-PACKAGE:{package_id}`) prevents ciphertext transplant attacks.
4. **Dynamic Access Control & Instant Revocation**:
   - Real-time grant revocation blocks recipients from downloading or accessing metadata immediately.
5. **Real-time Performance Benchmarking Suite & Dashboard**:
   - Interactive React dashboard (`/perf`) and CLI benchmark runner (`scripts/benchmark_runner.py`) comparing latency, sizes, and throughput.

---

## 4. Benchmark Highlights

| Metric | Post-Quantum (ML-KEM / ML-DSA) | Classical (X25519 / Ed25519) | Analysis |
| :--- | :--- | :--- | :--- |
| **Key Generation** | ~0.06 ms | ~0.05 ms | Negligible CPU difference (<0.01ms) |
| **Encapsulation / Exchange** | ~0.16 ms | ~0.14 ms | Sub-millisecond speed for enterprise scale |
| **Signing Latency** | ~0.10 ms | ~0.09 ms | High-throughput document signing |
| **Public Key Size** | 1,184 Bytes | 32 Bytes | 37x size overhead, easily handled by web APIs |
| **Signature Size** | 3,309 Bytes | 64 Bytes | 51.7x size overhead, verified instantly |

---

## 5. Live Demonstration & Verification

Run the interactive demonstration script with zero external configuration:
```bash
python scripts/demo.py
```

Run comparative benchmarks across PQC and Classical primitives:
```bash
python scripts/benchmark_runner.py -n 50
```

Run the complete automated test suite (373 tests):
```bash
pytest
```
