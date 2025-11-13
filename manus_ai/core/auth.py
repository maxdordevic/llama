"""
Authentication and API Key Management System
Handles user authentication, API keys, and authorization
"""

import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import jwt
import bcrypt

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    API_ONLY = "api_only"


class Permission(str, Enum):
    """Permissions"""
    # Session permissions
    CREATE_SESSION = "session:create"
    READ_SESSION = "session:read"
    UPDATE_SESSION = "session:update"
    DELETE_SESSION = "session:delete"

    # Agent permissions
    EXECUTE_AGENT = "agent:execute"
    MANAGE_AGENT = "agent:manage"

    # Plugin permissions
    INSTALL_PLUGIN = "plugin:install"
    MANAGE_PLUGIN = "plugin:manage"

    # Admin permissions
    MANAGE_USERS = "user:manage"
    VIEW_ANALYTICS = "analytics:view"
    MANAGE_SYSTEM = "system:manage"

    # API key permissions
    CREATE_API_KEY = "apikey:create"
    REVOKE_API_KEY = "apikey:revoke"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.CREATE_SESSION,
        Permission.READ_SESSION,
        Permission.UPDATE_SESSION,
        Permission.DELETE_SESSION,
        Permission.EXECUTE_AGENT,
        Permission.MANAGE_AGENT,
        Permission.INSTALL_PLUGIN,
        Permission.MANAGE_PLUGIN,
        Permission.MANAGE_USERS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_SYSTEM,
        Permission.CREATE_API_KEY,
        Permission.REVOKE_API_KEY
    },
    UserRole.USER: {
        Permission.CREATE_SESSION,
        Permission.READ_SESSION,
        Permission.UPDATE_SESSION,
        Permission.DELETE_SESSION,
        Permission.EXECUTE_AGENT,
        Permission.CREATE_API_KEY,
        Permission.REVOKE_API_KEY
    },
    UserRole.READONLY: {
        Permission.READ_SESSION,
        Permission.VIEW_ANALYTICS
    },
    UserRole.API_ONLY: {
        Permission.CREATE_SESSION,
        Permission.EXECUTE_AGENT
    }
}


@dataclass
class User:
    """User account"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIKey:
    """API key"""
    key_id: str
    user_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True
    permissions: Set[Permission] = field(default_factory=set)
    rate_limit: Optional[int] = None  # Requests per minute
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Authentication session"""
    session_id: str
    user_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_valid: bool = True


class PasswordHasher:
    """Handles password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False


class APIKeyManager:
    """Manages API keys"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_api_key(self) -> str:
        """Generate a new API key"""
        # Format: mk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (32 random chars)
        return f"mk_{secrets.token_urlsafe(32)}"

    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str, key_hash: str) -> bool:
        """Verify API key against hash"""
        computed_hash = self.hash_api_key(api_key)
        return hmac.compare_digest(computed_hash, key_hash)


class JWTManager:
    """Manages JWT tokens"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.logger = logging.getLogger(__name__)

    def create_token(
        self,
        user_id: str,
        role: UserRole,
        expires_in_hours: int = 24
    ) -> str:
        """
        Create JWT token

        Args:
            user_id: User ID
            role: User role
            expires_in_hours: Token expiration in hours

        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expiration = now + timedelta(hours=expires_in_hours)

        payload = {
            "user_id": user_id,
            "role": role.value,
            "iat": now.timestamp(),
            "exp": expiration.timestamp(),
            "type": "access"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None

    def refresh_token(self, token: str, expires_in_hours: int = 24) -> Optional[str]:
        """
        Refresh JWT token

        Args:
            token: Current JWT token
            expires_in_hours: New expiration in hours

        Returns:
            New JWT token if valid, None otherwise
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        return self.create_token(
            payload["user_id"],
            UserRole(payload["role"]),
            expires_in_hours
        )


class AuthenticationManager:
    """Central authentication manager"""

    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        storage_backend: Optional[Any] = None
    ):
        """
        Initialize authentication manager

        Args:
            jwt_secret: Secret key for JWT tokens
            storage_backend: Optional storage backend
        """
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.storage = storage_backend

        self.password_hasher = PasswordHasher()
        self.api_key_manager = APIKeyManager()
        self.jwt_manager = JWTManager(self.jwt_secret)

        # In-memory storage (replace with database in production)
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.sessions: Dict[str, Session] = {}

        self.logger = logging.getLogger(__name__)

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER
    ) -> User:
        """
        Create a new user

        Args:
            username: Username
            email: Email address
            password: Plain text password
            role: User role

        Returns:
            Created user
        """
        # Check if user exists
        if any(u.username == username for u in self.users.values()):
            raise ValueError(f"Username already exists: {username}")

        if any(u.email == email for u in self.users.values()):
            raise ValueError(f"Email already exists: {email}")

        # Hash password
        password_hash = self.password_hasher.hash_password(password)

        # Create user
        user_id = secrets.token_urlsafe(16)
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            created_at=datetime.utcnow()
        )

        self.users[user_id] = user
        self.logger.info(f"Created user: {username} ({user_id})")

        return user

    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate user with username and password

        Args:
            username: Username
            password: Password

        Returns:
            User if authenticated, None otherwise
        """
        # Find user
        user = next(
            (u for u in self.users.values() if u.username == username),
            None
        )

        if not user:
            self.logger.warning(f"User not found: {username}")
            return None

        if not user.is_active:
            self.logger.warning(f"User inactive: {username}")
            return None

        # Verify password
        if not self.password_hasher.verify_password(password, user.password_hash):
            self.logger.warning(f"Invalid password for user: {username}")
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        self.logger.info(f"User authenticated: {username}")

        return user

    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """
        Create authentication session

        Args:
            user: Authenticated user
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created session
        """
        # Create JWT token
        token = self.jwt_manager.create_token(user.user_id, user.role)

        # Create session
        session_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()

        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            token=token,
            created_at=now,
            expires_at=now + timedelta(hours=24),
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.sessions[session_id] = session
        self.logger.info(f"Created session for user: {user.username}")

        return session

    async def verify_session(self, token: str) -> Optional[Session]:
        """
        Verify session token

        Args:
            token: JWT token

        Returns:
            Session if valid, None otherwise
        """
        # Verify JWT
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            return None

        # Find session
        session = next(
            (s for s in self.sessions.values() if s.token == token),
            None
        )

        if not session:
            return None

        if not session.is_valid:
            return None

        # Check expiration
        if datetime.utcnow() > session.expires_at:
            session.is_valid = False
            return None

        # Update last activity
        session.last_activity = datetime.utcnow()

        return session

    async def create_api_key(
        self,
        user: User,
        name: str,
        permissions: Optional[Set[Permission]] = None,
        expires_in_days: Optional[int] = None,
        rate_limit: Optional[int] = None
    ) -> tuple[APIKey, str]:
        """
        Create API key

        Args:
            user: User who owns the key
            name: Key name/description
            permissions: Optional specific permissions (defaults to user's role permissions)
            expires_in_days: Optional expiration in days
            rate_limit: Optional rate limit (requests per minute)

        Returns:
            Tuple of (APIKey object, plain text key)
        """
        # Generate key
        plain_key = self.api_key_manager.generate_api_key()
        key_hash = self.api_key_manager.hash_api_key(plain_key)

        # Set permissions
        if permissions is None:
            permissions = ROLE_PERMISSIONS.get(user.role, set())

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create API key
        key_id = secrets.token_urlsafe(16)
        api_key = APIKey(
            key_id=key_id,
            user_id=user.user_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            permissions=permissions,
            rate_limit=rate_limit
        )

        self.api_keys[key_id] = api_key
        self.logger.info(f"Created API key for user {user.username}: {name}")

        return api_key, plain_key

    async def verify_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Verify API key

        Args:
            api_key: Plain text API key

        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = self.api_key_manager.hash_api_key(api_key)

        # Find matching key
        for key_obj in self.api_keys.values():
            if self.api_key_manager.verify_api_key(api_key, key_obj.key_hash):
                if not key_obj.is_active:
                    return None

                # Check expiration
                if key_obj.expires_at and datetime.utcnow() > key_obj.expires_at:
                    key_obj.is_active = False
                    return None

                # Update last used
                key_obj.last_used = datetime.utcnow()
                return key_obj

        return None

    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            self.logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    def has_permission(
        self,
        user: Optional[User],
        api_key: Optional[APIKey],
        permission: Permission
    ) -> bool:
        """
        Check if user/API key has permission

        Args:
            user: User object
            api_key: API key object
            permission: Required permission

        Returns:
            True if authorized
        """
        if api_key:
            return permission in api_key.permissions

        if user:
            return permission in ROLE_PERMISSIONS.get(user.role, set())

        return False

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)

    async def list_user_api_keys(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user"""
        return [key for key in self.api_keys.values() if key.user_id == user_id]

    async def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if now > session.expires_at or not session.is_valid
        ]

        for sid in expired:
            del self.sessions[sid]

        if expired:
            self.logger.info(f"Cleaned up {len(expired)} expired sessions")


# Global auth manager instance
_auth_manager_instance: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get global auth manager instance"""
    global _auth_manager_instance
    if _auth_manager_instance is None:
        _auth_manager_instance = AuthenticationManager()
    return _auth_manager_instance
