# PQC-Secure Cryptographic Security Model & Threat Assessment

---

## 1. Threat Model & Adversary Capabilities

The PQC-Secure platform is designed under the **Post-Quantum Adversary Model**, defending against both classical adversaries and adversaries equipped with Cryptanalytically Relevant Quantum Computers (CRQC).

### Adversary Profiles
1. **Passive Eavesdropper with Quantum Storage ("Harvest Now, Decrypt Later")**:
   - Captures encrypted network traffic and stored file packages today.
   - Retains ciphertext indefinitely until a sufficiently large quantum computer running Shor's algorithm becomes operational.
   - **Mitigation**: ML-KEM-768 (Module Lattice-based Key Encapsulation) provides NIST Category 3 security (equivalent to AES-192/256), immune to Shor's and Grover's algorithm attacks.
2. **Active Man-in-the-Middle (MitM) & Tampering Adversary**:
   - Modifies ciphertext payloads, manifest metadata, or wrapped key components in transit or on storage.
   - Attempts identity spoofing and forgery.
   - **Mitigation**: ML-DSA-65 (Module Lattice-based Digital Signatures) signs the canonical JSON manifest. AES-256-GCM ensures authenticated encryption with 128-bit authentication tags and context-bound Additional Authenticated Data (AAD).
3. **Malicious or Compromised Recipient**:
   - Attempts to access packages after grant revocation or decrypt files shared with other users.
   - **Mitigation**: Per-recipient key encapsulation; CEK is uniquely wrapped for each authorized user. Revocation invalidates grants in the access control layer and rejects decapsulation.

---

## 2. Cryptographic Architecture & Algorithm Selection

| Layer | Algorithm / Standard | Purpose | Quantum Security Level |
| :--- | :--- | :--- | :--- |
| **KEM (Post-Quantum)** | ML-KEM-768 (NIST FIPS 203) | Key encapsulation for recipient CEK wrapping | NIST Category 3 (128+ bits quantum) |
| **Signature (Post-Quantum)** | ML-DSA-65 (NIST FIPS 204) | Canonical manifest digital signature | NIST Category 3 (128+ bits quantum) |
| **Key Agreement (Classical)** | X25519 (RFC 7748) | Ephemeral ECDH key exchange | Classical 128-bit (Vulnerable to Shor's) |
| **Signature (Classical)** | Ed25519 (RFC 8032) | Manifest digital signature | Classical 128-bit (Vulnerable to Shor's) |
| **Symmetric Encryption** | AES-256-GCM (NIST SP 800-38D) | Payload data encryption | 128-bit quantum security (Grover-resistant) |
| **Key Derivation** | HKDF-SHA-256 (RFC 5869) | Wrap key derivation from shared secret | 128-bit quantum security |

---

## 3. Envelope Encryption Pipeline

```
[Plaintext File]
       |
       v (AES-256-GCM with Random CEK)
[Encrypted Payload] = Nonce (12B) + Ciphertext + Tag (16B)
       |
       +--> Stored on Persistent Storage (S3 / MinIO)

For Each Recipient:
[ML-KEM-768 Encapsulate(Recipient PubKey)] -> (Ciphertext, SharedSecret)
       |
       v (HKDF-SHA-256 with Context Info "PQC-CEK-WRAP:{sender}:{recipient}:1.0")
[Wrap Key (256-bit)]
       |
       v (AES-256-GCM Encrypt CEK)
[Wrapped CEK] = WrapNonce (12B) + EncryptedCEK + Tag (16B)

[Canonical Manifest JSON]
       |
       v (ML-DSA-65 Sign with Sender Private Key)
[Digital Signature]
```

### Context Binding via Additional Authenticated Data (AAD)
During payload encryption, the package UUID is bound to the AES-GCM ciphertext via:
`AAD = "PQC-PACKAGE:" || package_id`
This prevents ciphertext cut-and-paste attacks where an attacker transfers encrypted payloads between different package manifests.

---

## 4. Tamper Resistance Verification Matrix

| Tampering Vector | Detection Mechanism | Error Code / Event |
| :--- | :--- | :--- |
| **Ciphertext payload byte corruption** | AES-256-GCM tag verification failure | HTTP 400 (`DecryptionFailedError`), `CRYPTO_VERIFICATION_FAILED` audit log |
| **Manifest metadata alteration** | ML-DSA-65 / Ed25519 signature verification failure | HTTP 400 (`SignatureVerificationError`), `CRYPTO_VERIFICATION_FAILED` audit log |
| **Digital signature byte modification** | ML-DSA / Ed25519 signature reject | HTTP 400 (`SignatureVerificationError`), `CRYPTO_VERIFICATION_FAILED` audit log |
| **GCM Nonce / Tag modification** | AES-256-GCM authentication failure | HTTP 400, `CRYPTO_VERIFICATION_FAILED` audit log |
| **Unauthorized recipient request** | Database access grant validation | HTTP 403 (`AccessDeniedError`), `ACCESS_DENIED` audit log |
| **Revoked grant request** | Grant status check (`status == revoked`) | HTTP 403 (`AccessDeniedError`), `ACCESS_DENIED` audit log |

---

## 5. Secrets Management & Privacy Guarantees

1. **Zero Secret Logging**: Application logging explicitly scrubs and excludes passwords, private key material, shared secrets, CEK bytes, and plaintext file contents.
2. **Forward Secrecy in Classical Mode**: Ephemeral X25519 keypairs are generated per-package and discarded immediately after key agreement.
3. **Session Hardening**: JWT tokens are signed with high-entropy keys, transmitted via secure `HttpOnly; SameSite=Lax` cookies, and validated on every API request.
