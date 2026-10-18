"""Input validation and sanitization service for security and hardening."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Set

from pqc_secure.core.config import settings

# RFC 5322 simplified email regex with strict domain structure
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
)

# Dangerous executable and script file extensions
DANGEROUS_EXTENSIONS: Set[str] = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".vbs",
    ".msi",
    ".dll",
    ".com",
    ".scr",
    ".pif",
    ".application",
    ".gadget",
    ".jar",
    ".hta",
    ".cpl",
}

# Recognized cryptographic algorithms
SUPPORTED_ALGORITHMS: Set[str] = {
    "ml-kem-768",
    "x25519",
    "ml-dsa-65",
    "ed25519",
    "aes-256-gcm",
}

SUPPORTED_KEM_ALGORITHMS: Set[str] = {"ml-kem-768", "x25519"}
SUPPORTED_SIG_ALGORITHMS: Set[str] = {"ml-dsa-65", "ed25519"}


def sanitize_text(text: Optional[str], max_length: int = 1000) -> str:
    """
    Sanitize text input:
    - Strip HTML tags and script elements.
    - Remove non-printable control characters except newline and tab.
    - Trim whitespace and enforce length limits.
    """
    if not text:
        return ""

    # Remove HTML/XML tags
    cleaned = re.sub(r"<[^>]*>", "", text)

    # Strip control characters except tab and newlines
    cleaned = "".join(ch for ch in cleaned if ch in "\t\n\r" or ord(ch) >= 32)

    # Normalize whitespace
    cleaned = cleaned.strip()

    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize uploaded filenames:
    - Eliminate path traversal sequences (../, ..\\).
    - Remove null bytes and special directory characters.
    - Ensure a clean basename with safe alphanumeric, dash, dot, and underscore characters.
    """
    if not filename:
        return "uploaded_file.bin"

    # Strip null bytes
    clean = filename.replace("\x00", "").strip()

    # Extract basename only
    base = os.path.basename(clean)
    base = Path(base).name

    # Remove directory traversal patterns
    base = re.sub(r"\.\.+[/\\Release]*", "", base)

    # Replace unsafe characters with underscore (keep a-z, A-Z, 0-9, ., _, -)
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", base)

    # Avoid hidden files or names starting with dot
    sanitized = sanitized.lstrip(".")

    # If filename is empty after sanitization, assign default
    if not sanitized or sanitized == "_":
        sanitized = "uploaded_file.bin"

    # Enforce maximum filename length
    if len(sanitized) > 255:
        stem = Path(sanitized).stem[:240]
        suffix = Path(sanitized).suffix[:14]
        sanitized = f"{stem}{suffix}"

    return sanitized


def validate_email_format(email: str) -> str:
    """
    Validate and normalize email address:
    - Check RFC 5322 format.
    - Prohibit consecutive dots or invalid domain parts.
    - Return normalized lowercase trimmed email.
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email address cannot be empty.")

    normalized = email.strip().lower()

    if len(normalized) > 254:
        raise ValueError("Email address exceeds maximum length of 254 characters.")

    if ".." in normalized:
        raise ValueError("Email address cannot contain consecutive periods.")

    if not EMAIL_REGEX.match(normalized):
        raise ValueError(f"Invalid email address format: '{email}'")

    return normalized


def validate_file_security(
    filename: str,
    file_size_bytes: int,
    allowed_extensions: Optional[Set[str]] = None,
) -> None:
    """
    Enforce security checks on file uploads:
    - Block dangerous executable and script extensions.
    - Enforce maximum configured file size.
    - Check non-negative file size.
    """
    if file_size_bytes < 0:
        raise ValueError("File size cannot be negative.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"File size ({file_size_bytes / (1024 * 1024):.1f} MB) exceeds maximum permitted size of {settings.max_file_size_mb} MB."
        )

    ext = Path(filename).suffix.lower()

    if ext in DANGEROUS_EXTENSIONS:
        raise ValueError(
            f"File extension '{ext}' is not permitted for security reasons (executable/script content blocked)."
        )

    if allowed_extensions and ext not in allowed_extensions:
        raise ValueError(
            f"File extension '{ext}' is not in the allowed extensions list: {', '.join(sorted(allowed_extensions))}."
        )


def validate_algorithm_selection(algorithm: str, category: Optional[str] = None) -> str:
    """
    Validate cryptographic algorithm selection:
    - Ensure algorithm is supported.
    - Verify category suitability (kem vs signature).
    - Return canonical normalized algorithm string.
    """
    if not algorithm:
        raise ValueError("Cryptographic algorithm must be specified.")

    norm = algorithm.strip().lower()

    if norm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. Supported algorithms: {', '.join(sorted(SUPPORTED_ALGORITHMS))}."
        )

    if category == "kem" and norm not in SUPPORTED_KEM_ALGORITHMS:
        raise ValueError(
            f"Algorithm '{norm}' is not a valid key establishment primitive. Expected one of: {', '.join(sorted(SUPPORTED_KEM_ALGORITHMS))}."
        )

    if category in ("signature", "sig") and norm not in SUPPORTED_SIG_ALGORITHMS:
        raise ValueError(
            f"Algorithm '{norm}' is not a valid digital signature primitive. Expected one of: {', '.join(sorted(SUPPORTED_SIG_ALGORITHMS))}."
        )

    return norm


def validate_crypto_mode(mode: str) -> str:
    """Validate encryption mode: pqc or classical."""
    if not mode:
        return "pqc"
    norm = mode.strip().lower()
    if norm not in ("pqc", "classical"):
        raise ValueError("Encryption mode must be either 'pqc' or 'classical'.")
    return norm
