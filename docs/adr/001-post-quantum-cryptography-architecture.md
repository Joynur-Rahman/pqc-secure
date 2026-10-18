# ADR 001: Post-Quantum Cryptography Architecture & NIST FIPS Selection

- **Status**: Accepted
- **Date**: 2026-10-18
- **Context**: Design of enterprise quantum-resilient file sharing and storage platform

---

## 1. Context and Problem Statement

Shor's algorithm running on a cryptanalytically relevant quantum computer (CRQC) will break traditional public-key cryptosystems, including RSA, Diffie-Hellman, and Elliptic Curve Cryptography (ECDH, ECDSA, Ed25519). Adversaries today practice "Harvest Now, Decrypt Later" (HNDL), storing intercepted encrypted communications and files to decrypt once quantum hardware matures.

We must select standardized post-quantum cryptographic primitives to provide long-term confidentiality and integrity while maintaining high throughput and reasonable overhead.

---

## 2. Decision Drivers

1. **Compliance & Standardization**: Must comply with final NIST Post-Quantum Cryptography standards (August 2024 FIPS releases).
2. **Performance & Overhead**: Key encapsulation mechanisms (KEM) and signatures must have acceptable sizes and sub-second latencies on standard server and client hardware.
3. **Hybrid Transition Support**: Must provide both post-quantum algorithms and battle-tested classical algorithms for phased migration and comparative benchmarking.
4. **Environment Portability**: Must operate seamlessly across Linux, Windows, macOS, and containerized Docker environments with or without native C library (`liboqs`) dependencies.

---

## 3. Considered Options

- **Option A**: Classic McEliece + SPHINCS+
  - *Cons*: Extremely large public keys (McEliece: ~250KB - 1MB; SPHINCS+: ~8-40KB signatures).
- **Option B**: NIST FIPS 203 (ML-KEM-768 / Kyber) + NIST FIPS 204 (ML-DSA-65 / Dilithium)
  - *Pros*: NIST standard; Module Lattice-based; balanced performance; reasonable key sizes (1184B public key, 1088B ciphertext, 1952B signature key).
- **Option C**: Classical-only (X25519 + Ed25519)
  - *Cons*: Zero protection against quantum adversaries and HNDL.

---

## 4. Decision Outcome

We selected **Option B**:
1. **Key Encapsulation**: **ML-KEM-768 (FIPS 203)** at NIST Security Category 3.
2. **Digital Signatures**: **ML-DSA-65 (FIPS 204)** at NIST Security Category 3.
3. **Symmetric Encryption**: **AES-256-GCM** with 256-bit Content Encryption Keys (CEK) and HKDF-SHA-256 key derivation.
4. **Hybrid Dual Mode**: Retain **X25519 / Ed25519** as an explicit selectable mode for benchmarking and transition support.
5. **Multi-Platform Fallback Emulation**: Incorporate a pure-Python RFC/FIPS-compliant lattice emulation fallback when native `liboqs` binaries are unavailable.

---

## 5. Consequences

### Positive
- Immune to Shor's algorithm attacks.
- Protection against "Harvest Now, Decrypt Later" threats.
- Fast encapsulation and decapsulation speeds (sub-millisecond).
- Built-in envelope encryption ensures payload scaling is independent of recipient count.

### Trade-offs
- Key and signature artifacts are larger than classical ECC (1184B vs 32B for public keys; 3309B vs 64B for signatures).
- Requires careful manifest serialization and canonical JSON formatting prior to signing.
