"""Comprehensive unit tests for Cryptographic Service Layer (Task 3.1).

Covers:
- ML-KEM-768 (KEM keygen, encap, decap, tampered ciphertext, invalid keys)
- ML-DSA-65 (Signature keygen, sign, verify, message tamper, signature tamper)
- X25519 (Key agreement, key sizes, mutual shared secrets)
- Ed25519 (Classical signatures, sign, verify, tampering)
- HKDF-SHA-256 (Key derivation, salt, info binding, length)
- AES-256-GCM (Authenticated encryption/decryption, fresh nonces, AAD, tampering)
- Utilities (Base64 encoding/decoding, key ID generation, algorithm validation)
"""
import pytest
import os
import secrets

from pqc_secure.services.crypto import (
    CryptoService,
    CryptoError,
    InvalidKeyError,
    DecryptionError,
)


class TestMLKEM768:
    """Tests for ML-KEM-768 post-quantum key encapsulation mechanism."""

    def test_kem_keypair_generation_sizes(self):
        """Test ML-KEM-768 key generation returns exact NIST specification sizes."""
        pub, priv = CryptoService.generate_keypair_kem()
        assert len(pub) == CryptoService.ML_KEM_768_PUBLIC_KEY_SIZE
        assert len(priv) == CryptoService.ML_KEM_768_PRIVATE_KEY_SIZE

    def test_kem_encapsulate_and_decapsulate_success(self):
        """Test complete ML-KEM-768 encapsulation and decapsulation round-trip."""
        pub, priv = CryptoService.generate_keypair_kem()
        ciphertext, sender_secret = CryptoService.encapsulate_kem(pub)

        assert len(ciphertext) == CryptoService.ML_KEM_768_CIPHERTEXT_SIZE
        assert len(sender_secret) == CryptoService.ML_KEM_768_SHARED_SECRET_SIZE

        recipient_secret = CryptoService.decapsulate_kem(ciphertext, priv)
        assert recipient_secret == sender_secret

    def test_kem_encapsulation_randomness(self):
        """Test that successive encapsulations produce distinct ciphertexts and shared secrets."""
        pub, _ = CryptoService.generate_keypair_kem()
        ct1, ss1 = CryptoService.encapsulate_kem(pub)
        ct2, ss2 = CryptoService.encapsulate_kem(pub)

        assert ct1 != ct2
        assert ss1 != ss2

    def test_kem_decapsulate_with_wrong_private_key(self):
        """Test decapsulation fails when attempted with a different private key."""
        pub1, priv1 = CryptoService.generate_keypair_kem()
        pub2, priv2 = CryptoService.generate_keypair_kem()

        ciphertext, sender_secret = CryptoService.encapsulate_kem(pub1)

        # Decapsulating with priv2 must either raise DecryptionError or yield different secret
        try:
            wrong_secret = CryptoService.decapsulate_kem(ciphertext, priv2)
            assert wrong_secret != sender_secret
        except (DecryptionError, CryptoError):
            pass  # Raising DecryptionError on mismatch is also expected behavior

    def test_kem_decapsulate_tampered_ciphertext(self):
        """Test that tampering with ciphertext fails decapsulation."""
        pub, priv = CryptoService.generate_keypair_kem()
        ciphertext, _ = CryptoService.encapsulate_kem(pub)

        # Corrupt one byte of ciphertext
        tampered = bytearray(ciphertext)
        tampered[15] ^= 0xFF

        with pytest.raises((DecryptionError, CryptoError)):
            CryptoService.decapsulate_kem(bytes(tampered), priv)

    def test_kem_invalid_public_key_size(self):
        """Test encapsulation rejects invalid public key sizes."""
        with pytest.raises(InvalidKeyError):
            CryptoService.encapsulate_kem(b"short_key")

    def test_kem_invalid_ciphertext_size(self):
        """Test decapsulation rejects invalid ciphertext size."""
        _, priv = CryptoService.generate_keypair_kem()
        with pytest.raises(DecryptionError):
            CryptoService.decapsulate_kem(b"invalid_length_ct", priv)

    def test_kem_invalid_private_key_size(self):
        """Test decapsulation rejects invalid private key size."""
        pub, _ = CryptoService.generate_keypair_kem()
        ciphertext, _ = CryptoService.encapsulate_kem(pub)
        with pytest.raises(InvalidKeyError):
            CryptoService.decapsulate_kem(ciphertext, b"short_priv")


class TestMLDSA65:
    """Tests for ML-DSA-65 post-quantum digital signature algorithm."""

    def test_dsa_keypair_generation_sizes(self):
        """Test ML-DSA-65 key generation returns exact NIST specification sizes."""
        pub, priv = CryptoService.generate_keypair_sig()
        assert len(pub) == CryptoService.ML_DSA_65_PUBLIC_KEY_SIZE
        assert len(priv) == CryptoService.ML_DSA_65_PRIVATE_KEY_SIZE

    def test_dsa_sign_and_verify_success(self):
        """Test signature generation and successful verification."""
        pub, priv = CryptoService.generate_keypair_sig()
        message = b"Canonical package manifest content to be signed"

        signature = CryptoService.sign_dsa(message, priv)
        assert len(signature) == CryptoService.ML_DSA_65_SIGNATURE_SIZE

        is_valid = CryptoService.verify_dsa(message, signature, pub)
        assert is_valid is True

    def test_dsa_verify_tampered_message(self):
        """Test verification fails if message content is modified."""
        pub, priv = CryptoService.generate_keypair_sig()
        message = b"Original manifest"
        signature = CryptoService.sign_dsa(message, priv)

        tampered_message = b"Modified manifest"
        assert CryptoService.verify_dsa(tampered_message, signature, pub) is False

    def test_dsa_verify_tampered_signature(self):
        """Test verification fails if signature byte is modified."""
        pub, priv = CryptoService.generate_keypair_sig()
        message = b"Manifest message"
        signature = bytearray(CryptoService.sign_dsa(message, priv))
        signature[10] ^= 0x01

        assert CryptoService.verify_dsa(message, bytes(signature), pub) is False

    def test_dsa_verify_wrong_public_key(self):
        """Test verification fails with another public key."""
        pub1, priv1 = CryptoService.generate_keypair_sig()
        pub2, _ = CryptoService.generate_keypair_sig()

        message = b"Important manifest"
        signature = CryptoService.sign_dsa(message, priv1)

        assert CryptoService.verify_dsa(message, signature, pub2) is False

    def test_dsa_invalid_private_key_length(self):
        """Test signing rejects private key of incorrect length."""
        with pytest.raises(InvalidKeyError):
            CryptoService.sign_dsa(b"message", b"short_priv_key")

    def test_dsa_invalid_public_key_or_signature_length_verify(self):
        """Test verification returns False on bad lengths without crashing."""
        assert CryptoService.verify_dsa(b"msg", b"bad_sig", b"bad_pub") is False


class TestX25519:
    """Tests for X25519 classical key agreement."""

    def test_x25519_keypair_sizes(self):
        """Test X25519 raw key pair lengths are 32 bytes each."""
        pub, priv = CryptoService.generate_keypair_x25519()
        assert len(pub) == 32
        assert len(priv) == 32

    def test_x25519_mutual_key_agreement(self):
        """Test that Alice and Bob derive the exact same shared secret."""
        alice_pub, alice_priv = CryptoService.generate_keypair_x25519()
        bob_pub, bob_priv = CryptoService.generate_keypair_x25519()

        alice_shared = CryptoService.agree_x25519(alice_priv, bob_pub)
        bob_shared = CryptoService.agree_x25519(bob_priv, alice_pub)

        assert len(alice_shared) == 32
        assert alice_shared == bob_shared

    def test_x25519_invalid_key_lengths(self):
        """Test X25519 raises InvalidKeyError on wrong key lengths."""
        pub, priv = CryptoService.generate_keypair_x25519()
        with pytest.raises(InvalidKeyError):
            CryptoService.agree_x25519(b"short", pub)
        with pytest.raises(InvalidKeyError):
            CryptoService.agree_x25519(priv, b"short")


class TestEd25519:
    """Tests for Ed25519 classical digital signatures."""

    def test_ed25519_keypair_sizes(self):
        """Test Ed25519 key pair lengths are 32 bytes each."""
        pub, priv = CryptoService.generate_keypair_ed25519()
        assert len(pub) == 32
        assert len(priv) == 32

    def test_ed25519_sign_and_verify_success(self):
        """Test sign and verification of message."""
        pub, priv = CryptoService.generate_keypair_ed25519()
        message = b"Classical package manifest"

        signature = CryptoService.sign_ed25519(message, priv)
        assert len(signature) == 64

        assert CryptoService.verify_ed25519(message, signature, pub) is True

    def test_ed25519_verify_tampered_message(self):
        """Test verification fails on modified message."""
        pub, priv = CryptoService.generate_keypair_ed25519()
        message = b"Real message"
        signature = CryptoService.sign_ed25519(message, priv)

        assert CryptoService.verify_ed25519(b"Fake message", signature, pub) is False

    def test_ed25519_verify_tampered_signature(self):
        """Test verification fails on altered signature."""
        pub, priv = CryptoService.generate_keypair_ed25519()
        message = b"Some data"
        sig = bytearray(CryptoService.sign_ed25519(message, priv))
        sig[0] ^= 0xFF

        assert CryptoService.verify_ed25519(message, bytes(sig), pub) is False

    def test_ed25519_invalid_key_length(self):
        """Test Ed25519 rejects incorrect private key length."""
        with pytest.raises(InvalidKeyError):
            CryptoService.sign_ed25519(b"msg", b"too_short")


class TestHKDFSHA256:
    """Tests for HKDF-SHA-256 key derivation."""

    def test_hkdf_deterministic_derivation(self):
        """Test that same inputs always derive identical key."""
        ikm = b"initial_key_material_secret"
        salt = b"unique_salt_value"
        info = b"context_information"

        k1 = CryptoService.derive_key(ikm, salt=salt, info=info, length=32)
        k2 = CryptoService.derive_key(ikm, salt=salt, info=info, length=32)

        assert len(k1) == 32
        assert k1 == k2

    def test_hkdf_domain_separation(self):
        """Test that different info strings produce completely distinct keys."""
        ikm = b"shared_master_secret"
        k1 = CryptoService.derive_key(ikm, info=b"purpose-encryption", length=32)
        k2 = CryptoService.derive_key(ikm, info=b"purpose-integrity", length=32)

        assert k1 != k2

    def test_hkdf_custom_lengths(self):
        """Test deriving keys of different lengths."""
        ikm = b"secret_seed"
        k16 = CryptoService.derive_key(ikm, length=16)
        k64 = CryptoService.derive_key(ikm, length=64)

        assert len(k16) == 16
        assert len(k64) == 64

    def test_hkdf_empty_key_material_raises(self):
        """Test that empty key material raises ValueError."""
        with pytest.raises(ValueError):
            CryptoService.derive_key(b"")


class TestAES256GCM:
    """Tests for AES-256-GCM authenticated encryption."""

    def test_aes_gcm_encrypt_decrypt_roundtrip(self):
        """Test standard AES-256-GCM encryption and decryption."""
        key = secrets.token_bytes(32)
        plaintext = b"Confidential file content that must be encrypted safely."

        nonce, ciphertext = CryptoService.encrypt_aes_gcm(key, plaintext)

        assert len(nonce) == 12
        assert len(ciphertext) == len(plaintext) + 16  # includes 16-byte authentication tag
        assert ciphertext != plaintext

        decrypted = CryptoService.decrypt_aes_gcm(key, nonce, ciphertext)
        assert decrypted == plaintext

    def test_aes_gcm_with_associated_data(self):
        """Test AES-256-GCM with authenticated associated data (AAD)."""
        key = secrets.token_bytes(32)
        plaintext = b"Sensitive payload"
        aad = b'{"sender": "alice@example.com", "version": "1.0"}'

        nonce, ciphertext = CryptoService.encrypt_aes_gcm(key, plaintext, associated_data=aad)
        decrypted = CryptoService.decrypt_aes_gcm(key, nonce, ciphertext, associated_data=aad)
        assert decrypted == plaintext

    def test_aes_gcm_aad_tamper_fails(self):
        """Test that tampering with associated data causes decryption failure."""
        key = secrets.token_bytes(32)
        plaintext = b"Protected data"
        aad = b"original_aad"

        nonce, ciphertext = CryptoService.encrypt_aes_gcm(key, plaintext, associated_data=aad)

        with pytest.raises(DecryptionError):
            CryptoService.decrypt_aes_gcm(key, nonce, ciphertext, associated_data=b"altered_aad")

    def test_aes_gcm_ciphertext_tamper_fails(self):
        """Test that tampering with ciphertext triggers tag verification failure."""
        key = secrets.token_bytes(32)
        plaintext = b"Integrity verified message"

        nonce, ciphertext = CryptoService.encrypt_aes_gcm(key, plaintext)

        tampered = bytearray(ciphertext)
        tampered[0] ^= 0x01

        with pytest.raises(DecryptionError):
            CryptoService.decrypt_aes_gcm(key, nonce, bytes(tampered))

    def test_aes_gcm_fresh_nonce_per_call(self):
        """Test that successive encrypt calls generate fresh unique nonces."""
        key = secrets.token_bytes(32)
        plaintext = b"Same message twice"

        nonce1, ct1 = CryptoService.encrypt_aes_gcm(key, plaintext)
        nonce2, ct2 = CryptoService.encrypt_aes_gcm(key, plaintext)

        assert nonce1 != nonce2
        assert ct1 != ct2

    def test_aes_gcm_invalid_key_length(self):
        """Test invalid key lengths are rejected."""
        with pytest.raises(ValueError):
            CryptoService.encrypt_aes_gcm(b"short_16_byte_key!", b"data")
        with pytest.raises(ValueError):
            CryptoService.decrypt_aes_gcm(b"short_16_byte_key!", b"0" * 12, b"ct")

    def test_aes_gcm_invalid_nonce_length(self):
        """Test invalid nonce lengths are rejected."""
        key = secrets.token_bytes(32)
        with pytest.raises(ValueError):
            CryptoService.encrypt_aes_gcm(key, b"data", nonce=b"bad_len")
        with pytest.raises(DecryptionError):
            CryptoService.decrypt_aes_gcm(key, b"bad_len", b"ciphertext_data")


class TestCryptoUtilities:
    """Tests for key encoding, decoding, key ID generation, and validation."""

    def test_base64_encode_decode_roundtrip(self):
        """Test Base64 encoding and decoding utilities."""
        raw = os.urandom(64)
        b64 = CryptoService.encode_base64(raw)
        assert isinstance(b64, str)
        assert CryptoService.decode_base64(b64) == raw

    def test_decode_base64_invalid_string(self):
        """Test decode_base64 raises InvalidKeyError on corrupt input."""
        with pytest.raises(InvalidKeyError):
            CryptoService.decode_base64("!@#$%^not_valid_b64===")

    def test_generate_key_id_format(self):
        """Test canonical key identifier format."""
        pub = b"sample_public_key_bytes_12345"
        key_id = CryptoService.generate_key_id("ML-KEM-768", pub)
        assert key_id.startswith("ml-kem-768:")
        parts = key_id.split(":")
        assert len(parts) == 2
        assert len(parts[1]) == 16  # 16-hex char SHA-256 prefix

    def test_validate_public_key_success(self):
        """Test validate_public_key on legitimate keys."""
        kem_pub, _ = CryptoService.generate_keypair_kem()
        assert CryptoService.validate_public_key("ml-kem-768", kem_pub) is True
        assert CryptoService.validate_public_key("kyber768", kem_pub) is True

        sig_pub, _ = CryptoService.generate_keypair_sig()
        assert CryptoService.validate_public_key("ml-dsa-65", sig_pub) is True
        assert CryptoService.validate_public_key("dilithium3", sig_pub) is True

        x_pub, _ = CryptoService.generate_keypair_x25519()
        assert CryptoService.validate_public_key("x25519", x_pub) is True

        ed_pub, _ = CryptoService.generate_keypair_ed25519()
        assert CryptoService.validate_public_key("ed25519", ed_pub) is True

    def test_validate_public_key_failures(self):
        """Test validate_public_key rejects wrong sizes or unknown algorithms."""
        assert CryptoService.validate_public_key("ml-kem-768", b"too_short") is False
        assert CryptoService.validate_public_key("x25519", b"short") is False
        assert CryptoService.validate_public_key("unknown-alg", b"any_data") is False

    def test_algorithm_classification_and_aliases(self):
        """Test get_algorithm_type and normalization aliases."""
        assert CryptoService.get_algorithm_type("ml-kem-768") == "pqc"
        assert CryptoService.get_algorithm_type("kyber768") == "pqc"
        assert CryptoService.get_algorithm_type("ml-dsa-65") == "pqc"
        assert CryptoService.get_algorithm_type("dilithium3") == "pqc"
        assert CryptoService.get_algorithm_type("x25519") == "classical"
        assert CryptoService.get_algorithm_type("ed25519") == "classical"

        assert CryptoService.is_valid_algorithm("ml-kem-768") is True
        assert CryptoService.is_valid_algorithm("RSA-4096") is False
