"""Storage abstraction service supporting local filesystem and object storage."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from pqc_secure.core.config import settings
from pqc_secure.core.logging import logger


class StorageService:
    """Storage provider for encrypted payloads and temporary upload chunks."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.storage_path)
        self.temp_path = self.base_path / "temp"
        self.packages_path = self.base_path / "packages"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure storage directory trees exist."""
        try:
            self.temp_path.mkdir(parents=True, exist_ok=True)
            self.packages_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create storage directories: {e}")

    def save_payload(self, storage_key: str, data: bytes) -> str:
        """Save encrypted package payload to persistent storage."""
        target_path = self.packages_path / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(data)
        return str(target_path)

    def read_payload(self, storage_key: str) -> bytes:
        """Read encrypted package payload from storage."""
        target_path = self.packages_path / storage_key
        if not target_path.exists():
            # Check if key was absolute path
            target_path = Path(storage_key)
            if not target_path.exists():
                raise FileNotFoundError(f"Payload not found for key: {storage_key}")
        with open(target_path, "rb") as f:
            return f.read()

    def delete_payload(self, storage_key: str) -> bool:
        """Delete payload from storage."""
        target_path = self.packages_path / storage_key
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def save_chunk(self, upload_id: str, chunk_number: int, data: bytes) -> int:
        """Save an uploaded chunk to temporary storage."""
        chunk_dir = self.temp_path / upload_id
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_file = chunk_dir / f"chunk_{chunk_number:05d}.part"
        with open(chunk_file, "wb") as f:
            f.write(data)
        return len(data)

    def assemble_chunks(self, upload_id: str, total_chunks: int) -> bytes:
        """Assemble all chunks for an upload_id in order and clean up temporary parts."""
        chunk_dir = self.temp_path / upload_id
        if not chunk_dir.exists():
            raise FileNotFoundError(f"No upload chunks found for upload_id: {upload_id}")

        assembled = bytearray()
        for idx in range(total_chunks):
            chunk_file = chunk_dir / f"chunk_{idx:05d}.part"
            if not chunk_file.exists():
                raise FileNotFoundError(
                    f"Missing chunk {idx} of {total_chunks} for upload_id: {upload_id}"
                )
            with open(chunk_file, "rb") as f:
                assembled.extend(f.read())

        # Clean up temporary chunk directory
        try:
            shutil.rmtree(chunk_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temp upload {upload_id}: {e}")

        return bytes(assembled)

    def cleanup_upload(self, upload_id: str) -> None:
        """Clean up temporary upload folder."""
        chunk_dir = self.temp_path / upload_id
        if chunk_dir.exists():
            shutil.rmtree(chunk_dir, ignore_errors=True)


# Default global instance
storage_service = StorageService()
