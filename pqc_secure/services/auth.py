"""Authentication service"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import jwt
import logging

# Cryptography imports
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

# Lazy import to avoid db initialization
from pqc_secure.core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Handle user authentication and session management"""
    
    def __init__(self):
        """Initialize authentication service"""
        self.password_hasher = None
        self.hash_algorithm = settings.password_hashing_algorithm
        
        # Initialize password hasher based on configuration
        if self.hash_algorithm == "argon2id" and ARGON2_AVAILABLE:
            self.password_hasher = PasswordHasher()
        elif self.hash_algorithm == "bcrypt" and BCRYPT_AVAILABLE:
            self.password_hasher = None  # bcrypt is used directly
        else:
            logger.warning(f"Configured hashing algorithm '{self.hash_algorithm}' not available. "
                         "Falling back to bcrypt if available.")
            if BCRYPT_AVAILABLE:
                self.hash_algorithm = "bcrypt"
            else:
                raise RuntimeError("No password hashing library available. "
                                 "Please install argon2-cffi or bcrypt.")
    
    def normalize_email(self, email: str) -> str:
        """
        Normalize email address by lowercasing and trimming whitespace.
        
        Args:
            email: Email address to normalize
            
        Returns:
            Normalized email address
        """
        return email.strip().lower()
    
    def validate_email_format(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic email format validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password against requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check minimum length
        if len(password) < settings.password_min_length:
            return False, f"Password must be at least {settings.password_min_length} characters long"
        
        # Check for complexity (at least one uppercase, one lowercase, one digit)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and numeric characters"
        
        return True, None
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using configured algorithm.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password
            
        Raises:
            RuntimeError: If no hashing algorithm is available
        """
        if self.hash_algorithm == "argon2id" and ARGON2_AVAILABLE:
            return self.password_hasher.hash(password)
        elif self.hash_algorithm == "bcrypt" and BCRYPT_AVAILABLE:
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        else:
            raise RuntimeError("No password hashing algorithm available")
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            if self.hash_algorithm == "argon2id" and ARGON2_AVAILABLE:
                self.password_hasher.verify(password_hash, password)
                return True
            elif self.hash_algorithm == "bcrypt" and BCRYPT_AVAILABLE:
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
        
        return False
    
    def generate_token(self, user_id: str, expires_in_minutes: Optional[int] = None) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: User ID to encode in token
            expires_in_minutes: Token expiration time in minutes (uses default if None)
            
        Returns:
            JWT token string
        """
        if expires_in_minutes is None:
            expires_in_minutes = settings.access_token_expire_minutes
        
        expire_time = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        payload = {
            "sub": user_id,
            "exp": expire_time,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a JWT token and extract user ID.
        
        Args:
            token: JWT token to verify
            
        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.info("Invalid token")
            return None
    
    def register_user(self, db: Session, email: str, password: str) -> Tuple[bool, Optional[object], Optional[str]]:
        """
        Register a new user with email and password.
        
        Args:
            db: Database session
            email: User email address
            password: User password
            
        Returns:
            Tuple of (success, user, error_message)
        """
        # Lazy import to avoid db initialization at module level
        from pqc_secure.db.models import User
        
        # Normalize email
        normalized_email = self.normalize_email(email)
        
        # Validate email format
        if not self.validate_email_format(normalized_email):
            return False, None, "Invalid email format"
        
        # Validate password
        is_valid, error_msg = self.validate_password(password)
        if not is_valid:
            return False, None, error_msg
        
        # Check for existing user with same email (case-insensitive)
        existing_user = db.query(User).filter(
            User.email == normalized_email
        ).first()
        
        if existing_user:
            # Don't reveal whether email is registered (security best practice)
            logger.warning(f"Registration attempt with existing email: {normalized_email}")
            return False, None, "Unable to create account. Please try again."
        
        # Hash password
        try:
            password_hash = self.hash_password(password)
        except RuntimeError as e:
            logger.error(f"Password hashing failed: {e}")
            return False, None, "Internal server error during registration"
        
        # Create user
        user = User(
            email=normalized_email,
            password_hash=password_hash,
            account_status="active"
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User registered successfully: {user.id}")
            return True, user, None
        except IntegrityError:
            db.rollback()
            logger.warning(f"Database integrity error during registration for {normalized_email}")
            return False, None, "Unable to create account. Please try again."
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during user registration: {e}")
            return False, None, "Internal server error during registration"
