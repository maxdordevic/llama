"""
Rate Limiting and Security Enhancements
Protects API from abuse and implements security best practices
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import re

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitRule:
    """Rate limit rule"""
    name: str
    limit: int  # Max requests
    period_seconds: int  # Time window
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    block_duration_seconds: int = 60  # How long to block after limit exceeded


@dataclass
class RateLimitState:
    """Rate limit state for a client"""
    requests: deque = field(default_factory=deque)
    tokens: float = 0.0
    last_refill: float = 0.0
    blocked_until: Optional[float] = None


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self):
        self.states: Dict[str, Dict[str, RateLimitState]] = defaultdict(dict)
        self.logger = logging.getLogger(__name__)

    def _get_state(self, client_id: str, rule_name: str) -> RateLimitState:
        """Get or create rate limit state for client"""
        if rule_name not in self.states[client_id]:
            self.states[client_id][rule_name] = RateLimitState()
        return self.states[client_id][rule_name]

    async def check_rate_limit(
        self,
        client_id: str,
        rule: RateLimitRule
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit

        Args:
            client_id: Client identifier (user ID, IP, API key, etc.)
            rule: Rate limit rule to apply

        Returns:
            Tuple of (allowed, info_dict)
        """
        state = self._get_state(client_id, rule.name)
        now = time.time()

        # Check if blocked
        if state.blocked_until and now < state.blocked_until:
            remaining_block = int(state.blocked_until - now)
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "blocked_for_seconds": remaining_block,
                "retry_after": remaining_block
            }

        # Apply strategy
        if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            allowed = await self._check_sliding_window(state, rule, now)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            allowed = await self._check_token_bucket(state, rule, now)
        elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            allowed = await self._check_fixed_window(state, rule, now)
        else:
            allowed = True

        if not allowed:
            # Block client
            state.blocked_until = now + rule.block_duration_seconds
            self.logger.warning(f"Rate limit exceeded for {client_id} on rule {rule.name}")

            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "limit": rule.limit,
                "period_seconds": rule.period_seconds,
                "retry_after": rule.block_duration_seconds
            }

        # Record request
        state.requests.append(now)

        # Calculate remaining requests
        requests_in_window = len([r for r in state.requests if now - r <= rule.period_seconds])
        remaining = max(0, rule.limit - requests_in_window)

        return True, {
            "allowed": True,
            "limit": rule.limit,
            "remaining": remaining,
            "reset_in_seconds": rule.period_seconds
        }

    async def _check_sliding_window(
        self,
        state: RateLimitState,
        rule: RateLimitRule,
        now: float
    ) -> bool:
        """Check using sliding window strategy"""
        # Remove old requests outside the window
        cutoff = now - rule.period_seconds
        while state.requests and state.requests[0] < cutoff:
            state.requests.popleft()

        # Check if within limit
        return len(state.requests) < rule.limit

    async def _check_token_bucket(
        self,
        state: RateLimitState,
        rule: RateLimitRule,
        now: float
    ) -> bool:
        """Check using token bucket strategy"""
        # Initialize
        if state.last_refill == 0:
            state.tokens = rule.limit
            state.last_refill = now
            return True

        # Refill tokens
        elapsed = now - state.last_refill
        refill_rate = rule.limit / rule.period_seconds
        tokens_to_add = elapsed * refill_rate
        state.tokens = min(rule.limit, state.tokens + tokens_to_add)
        state.last_refill = now

        # Check if token available
        if state.tokens >= 1:
            state.tokens -= 1
            return True

        return False

    async def _check_fixed_window(
        self,
        state: RateLimitState,
        rule: RateLimitRule,
        now: float
    ) -> bool:
        """Check using fixed window strategy"""
        window_start = int(now / rule.period_seconds) * rule.period_seconds

        # Remove requests from previous windows
        while state.requests and state.requests[0] < window_start:
            state.requests.popleft()

        return len(state.requests) < rule.limit

    def reset_client(self, client_id: str):
        """Reset rate limit for client"""
        if client_id in self.states:
            del self.states[client_id]

    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit stats for client"""
        if client_id not in self.states:
            return {}

        stats = {}
        for rule_name, state in self.states[client_id].items():
            stats[rule_name] = {
                "request_count": len(state.requests),
                "blocked": state.blocked_until is not None and time.time() < state.blocked_until,
                "blocked_until": state.blocked_until
            }

        return stats


class InputValidator:
    """Validates and sanitizes user input"""

    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<embed",
        r"<object"
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"\$\{.*\}",
        r"\$\(.*\)",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_text_input(
        self,
        text: str,
        max_length: int = 10000,
        allow_html: bool = False,
        allow_code: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Validate text input

        Args:
            text: Input text
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML
            allow_code: Whether to allow code

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return True, None

        # Check length
        if len(text) > max_length:
            return False, f"Input too long (max {max_length} characters)"

        # Check for SQL injection
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(f"SQL injection attempt detected: {pattern}")
                return False, "Potentially malicious input detected"

        # Check for XSS if HTML not allowed
        if not allow_html:
            for pattern in self.XSS_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    self.logger.warning(f"XSS attempt detected: {pattern}")
                    return False, "HTML/JavaScript not allowed in input"

        # Check for command injection if code not allowed
        if not allow_code:
            for pattern in self.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, text):
                    self.logger.warning(f"Command injection attempt detected")
                    return False, "Command characters not allowed in input"

        return True, None

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path components
        filename = filename.replace("../", "").replace("..\\", "")
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove special characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")

        return filename

    def validate_email(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_url(self, url: str, allowed_schemes: List[str] = ["http", "https"]) -> bool:
        """Validate URL format and scheme"""
        pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, url, re.IGNORECASE):
            return False

        # Check scheme
        scheme = url.split("://")[0].lower()
        return scheme in allowed_schemes


class SecurityScanner:
    """Scans for security vulnerabilities"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def scan_code_execution(self, code: str) -> Dict[str, Any]:
        """
        Scan code for security issues before execution

        Args:
            code: Code to scan

        Returns:
            Scan results
        """
        issues = []

        # Check for dangerous imports
        dangerous_imports = [
            "os", "subprocess", "sys", "eval", "exec",
            "compile", "__import__", "open", "file"
        ]

        for danger in dangerous_imports:
            if re.search(rf'\b{danger}\b', code):
                issues.append({
                    "severity": "high",
                    "type": "dangerous_import",
                    "description": f"Dangerous import/function detected: {danger}"
                })

        # Check for file operations
        file_patterns = [r'open\(', r'\.write\(', r'\.read\(']
        for pattern in file_patterns:
            if re.search(pattern, code):
                issues.append({
                    "severity": "medium",
                    "type": "file_operation",
                    "description": "File operation detected"
                })

        # Check for network operations
        network_patterns = [r'requests\.', r'urllib', r'socket\.',  r'http\.']
        for pattern in network_patterns:
            if re.search(pattern, code):
                issues.append({
                    "severity": "medium",
                    "type": "network_operation",
                    "description": "Network operation detected"
                })

        return {
            "safe": len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "risk_level": "high" if any(i["severity"] == "high" for i in issues) else
                         "medium" if any(i["severity"] == "medium" for i in issues) else "low"
        }

    async def scan_prompt_injection(self, prompt: str) -> Dict[str, Any]:
        """
        Scan for prompt injection attempts

        Args:
            prompt: User prompt to scan

        Returns:
            Scan results
        """
        issues = []

        # Check for system prompt override attempts
        override_patterns = [
            r"ignore\s+(previous|all)\s+instructions",
            r"disregard\s+(previous|all)\s+instructions",
            r"you\s+are\s+now",
            r"new\s+instructions",
            r"system\s*:",
            r"developer\s+mode"
        ]

        for pattern in override_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append({
                    "type": "prompt_override",
                    "pattern": pattern,
                    "description": "Potential prompt injection attempt"
                })

        # Check for data exfiltration attempts
        exfil_patterns = [
            r"repeat\s+the\s+(above|previous)",
            r"what\s+were\s+your\s+instructions",
            r"show\s+me\s+your\s+system\s+prompt"
        ]

        for pattern in exfil_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append({
                    "type": "data_exfiltration",
                    "pattern": pattern,
                    "description": "Potential data exfiltration attempt"
                })

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "risk_level": "high" if len(issues) > 2 else "medium" if len(issues) > 0 else "low"
        }


class SecurityManager:
    """Central security management"""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.input_validator = InputValidator()
        self.security_scanner = SecurityScanner()
        self.logger = logging.getLogger(__name__)

        # Default rate limit rules
        self.rules = {
            "api_requests": RateLimitRule(
                name="api_requests",
                limit=100,
                period_seconds=60,
                block_duration_seconds=60
            ),
            "chat_messages": RateLimitRule(
                name="chat_messages",
                limit=50,
                period_seconds=60,
                block_duration_seconds=120
            ),
            "agent_executions": RateLimitRule(
                name="agent_executions",
                limit=20,
                period_seconds=60,
                block_duration_seconds=300
            ),
            "image_generations": RateLimitRule(
                name="image_generations",
                limit=10,
                period_seconds=300,
                block_duration_seconds=600
            ),
            "file_uploads": RateLimitRule(
                name="file_uploads",
                limit=20,
                period_seconds=60,
                block_duration_seconds=180
            )
        }

    async def check_request(
        self,
        client_id: str,
        rule_name: str,
        input_text: Optional[str] = None,
        code: Optional[str] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Comprehensive security check

        Args:
            client_id: Client identifier
            rule_name: Rate limit rule name
            input_text: Optional user input to validate
            code: Optional code to scan

        Returns:
            Tuple of (allowed, details)
        """
        # Check rate limit
        if rule_name in self.rules:
            allowed, rate_info = await self.rate_limiter.check_rate_limit(
                client_id,
                self.rules[rule_name]
            )

            if not allowed:
                return False, rate_info

        # Validate input
        if input_text:
            valid, error = self.input_validator.validate_text_input(input_text)
            if not valid:
                self.logger.warning(f"Invalid input from {client_id}: {error}")
                return False, {
                    "allowed": False,
                    "reason": "invalid_input",
                    "error": error
                }

            # Scan for prompt injection
            prompt_scan = await self.security_scanner.scan_prompt_injection(input_text)
            if not prompt_scan["safe"]:
                self.logger.warning(f"Prompt injection detected from {client_id}")
                return False, {
                    "allowed": False,
                    "reason": "prompt_injection_detected",
                    "details": prompt_scan
                }

        # Scan code
        if code:
            code_scan = await self.security_scanner.scan_code_execution(code)
            if not code_scan["safe"]:
                self.logger.warning(f"Unsafe code from {client_id}")
                return False, {
                    "allowed": False,
                    "reason": "unsafe_code",
                    "details": code_scan
                }

        return True, {"allowed": True}

    def add_rule(self, rule: RateLimitRule):
        """Add custom rate limit rule"""
        self.rules[rule.name] = rule

    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get security stats for client"""
        return {
            "rate_limits": self.rate_limiter.get_client_stats(client_id)
        }


# Global security manager instance
_security_manager_instance: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager_instance
    if _security_manager_instance is None:
        _security_manager_instance = SecurityManager()
    return _security_manager_instance
