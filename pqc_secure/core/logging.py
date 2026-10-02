"""Logging configuration"""
import logging
from logging.handlers import RotatingFileHandler
import os
from pqc_secure.core.config import settings


class SecretFilteringFormatter(logging.Formatter):
    """Custom formatter that filters out sensitive information from logs"""
    
    # Patterns to exclude from logs
    SENSITIVE_PATTERNS = [
        'password', 'secret', 'token', 'private_key', 'plaintext',
        'ciphertext', 'shared_secret', 'nonce', 'key_material',
        'authentication_tag', 'signature', 'api_key', 'access_key'
    ]
    
    def format(self, record):
        # Get the formatted message
        msg = super().format(record)
        
        # Filter out sensitive information
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.lower() in msg.lower():
                # Redact sensitive values but keep the key names
                msg = self._redact_sensitive_values(msg, pattern)
        
        return msg
    
    @staticmethod
    def _redact_sensitive_values(msg: str, pattern: str) -> str:
        """Redact sensitive values while preserving log structure"""
        # Simple redaction - replace actual values with [REDACTED]
        import re
        # Match patterns like:
        # - password=xxx
        # - password_hash=xxx
        # - "password": "value"
        # - "password":"value"
        # - PASSWORD=xxx
        # This regex handles quoted keys and values
        regex_pattern = r'["\']?' + pattern + r'\b["\']?\s*[:=]\s*["\']?[^"\',}\]]+["\']?'
        msg = re.sub(
            regex_pattern,
            f'{pattern}=[REDACTED]',
            msg,
            flags=re.IGNORECASE
        )
        return msg


def setup_logging():
    """Configure application logging based on settings"""
    logger = logging.getLogger("pqc_secure")
    logger.setLevel(settings.get_log_level())
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with secret filtering
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.get_log_level())
    formatter = SecretFilteringFormatter(settings.log_format)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (if configured)
    if settings.log_file:
        log_dir = os.path.dirname(settings.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(settings.get_log_level())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


logger = setup_logging()

