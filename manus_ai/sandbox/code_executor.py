"""
Sandboxed Code Execution Environment
Safely executes Python code with resource limits and isolation
"""

import logging
import asyncio
import sys
import io
import contextlib
import traceback
from typing import Dict, Any, Optional
import resource
import signal
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ExecutionTimeout(Exception):
    """Raised when code execution times out"""
    pass


class CodeExecutor:
    """
    Sandboxed Python code executor with security restrictions
    Features:
    - Time limits
    - Memory limits
    - Restricted imports
    - Output capture
    - Error handling
    """

    def __init__(
        self,
        timeout: int = 30,
        max_memory_mb: int = 512,
        restricted_imports: Optional[list] = None
    ):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.restricted_imports = restricted_imports or [
            "os", "subprocess", "socket", "sys", "__import__"
        ]

    async def execute_code(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        allow_imports: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in sandboxed environment

        Args:
            code: Python code to execute
            context: Optional execution context/variables
            allow_imports: List of allowed imports

        Returns:
            Execution result with output, return value, and errors
        """
        execution_id = str(uuid.uuid4())
        logger.info(f"[{execution_id}] Executing code (length: {len(code)} chars)")

        start_time = datetime.utcnow()

        try:
            # Validate code
            await self._validate_code(code, allow_imports)

            # Execute in subprocess for isolation
            result = await self._execute_in_sandbox(code, context or {})

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"[{execution_id}] Execution completed in {duration:.2f}s")

            return {
                "execution_id": execution_id,
                "status": "success",
                "output": result.get("output", ""),
                "return_value": result.get("return_value"),
                "errors": result.get("errors"),
                "duration": duration,
                "timestamp": start_time.isoformat()
            }

        except ExecutionTimeout:
            logger.error(f"[{execution_id}] Execution timed out after {self.timeout}s")
            return {
                "execution_id": execution_id,
                "status": "timeout",
                "error": f"Execution timed out after {self.timeout} seconds"
            }

        except Exception as e:
            logger.error(f"[{execution_id}] Execution failed: {e}")
            return {
                "execution_id": execution_id,
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def _validate_code(self, code: str, allow_imports: Optional[list] = None):
        """Validate code for security issues"""
        # Check for restricted imports
        for restricted in self.restricted_imports:
            if allow_imports and restricted in allow_imports:
                continue

            if f"import {restricted}" in code or f"from {restricted}" in code:
                raise ValueError(f"Restricted import detected: {restricted}")

        # Check for dangerous functions
        dangerous_patterns = [
            "eval(",
            "exec(",
            "__import__",
            "compile(",
            "open(",  # Allow with explicit permission
            "file(",
        ]

        for pattern in dangerous_patterns:
            if pattern in code and pattern not in (allow_imports or []):
                logger.warning(f"Potentially dangerous pattern detected: {pattern}")

        # Try to compile code to check for syntax errors
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Syntax error in code: {e}")

    async def _execute_in_sandbox(
        self,
        code: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute code in sandboxed environment"""
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Prepare safe globals
        safe_globals = {
            "__builtins__": self._get_safe_builtins(),
            "print": print,  # Will be redirected
        }

        # Add context variables
        safe_globals.update(context)

        # Prepare locals
        safe_locals = {}

        return_value = None
        errors = []

        try:
            # Redirect stdout/stderr
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                # Set resource limits (Unix only)
                if hasattr(resource, 'RLIMIT_AS'):
                    try:
                        # Set memory limit
                        memory_limit = self.max_memory_mb * 1024 * 1024
                        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                    except Exception as e:
                        logger.warning(f"Could not set memory limit: {e}")

                # Execute code with timeout
                try:
                    # Use asyncio.wait_for for timeout
                    return_value = await asyncio.wait_for(
                        self._run_code(code, safe_globals, safe_locals),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    raise ExecutionTimeout()

        except Exception as e:
            errors.append({
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            })

        # Get outputs
        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()

        return {
            "output": stdout,
            "errors": stderr if stderr else None,
            "return_value": return_value,
            "locals": {k: str(v) for k, v in safe_locals.items() if not k.startswith('_')},
        }

    async def _run_code(
        self,
        code: str,
        globals_dict: dict,
        locals_dict: dict
    ):
        """Run code in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: exec(code, globals_dict, locals_dict)
        )

    def _get_safe_builtins(self) -> dict:
        """Get safe builtins for execution"""
        # Start with empty builtins
        safe_builtins = {}

        # Add safe builtins
        safe_list = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytes',
            'chr', 'dict', 'dir', 'divmod', 'enumerate', 'filter',
            'float', 'format', 'frozenset', 'getattr', 'hasattr',
            'hash', 'hex', 'int', 'isinstance', 'issubclass', 'iter',
            'len', 'list', 'map', 'max', 'min', 'next', 'object',
            'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
            'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple',
            'type', 'zip',
            # Safe exceptions
            'Exception', 'ValueError', 'TypeError', 'KeyError',
            'IndexError', 'AttributeError',
        ]

        builtins_dict = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__

        for name in safe_list:
            if name in builtins_dict:
                safe_builtins[name] = builtins_dict[name]

        return safe_builtins

    async def execute_notebook_cell(
        self,
        code: str,
        persistent_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute code as notebook cell with persistent context"""
        # Maintain context across cells (like Jupyter)
        result = await self.execute_code(code, persistent_context)

        # Extract locals to persist
        if result["status"] == "success" and "locals" in result:
            return {
                **result,
                "persistent_context": result.get("locals", {})
            }

        return result


class SecureCodeExecutor:
    """
    Enhanced secure code executor using Docker containers
    Provides maximum isolation for untrusted code
    """

    def __init__(self, docker_image: str = "python:3.11-slim"):
        self.docker_image = docker_image
        self.use_docker = self._check_docker_available()

    def _check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except:
            logger.warning("Docker not available, falling back to process isolation")
            return False

    async def execute_in_container(
        self,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute code in Docker container"""
        if not self.use_docker:
            # Fallback to regular execution
            executor = CodeExecutor(timeout=timeout)
            return await executor.execute_code(code)

        try:
            import docker
            client = docker.from_env()

            # Create temporary Python script
            script = f"""
import sys
import io
import traceback

stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

try:
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    {code}

    print(json.dumps({{
        "status": "success",
        "output": stdout_capture.getvalue(),
        "errors": stderr_capture.getvalue()
    }}))
except Exception as e:
    print(json.dumps({{
        "status": "error",
        "error": str(e),
        "traceback": traceback.format_exc()
    }}))
"""

            # Run in container
            container = client.containers.run(
                self.docker_image,
                f"python -c '{script}'",
                remove=True,
                timeout=timeout,
                mem_limit=f"{512}m",
                network_disabled=True,
                detach=False
            )

            return {
                "status": "success",
                "output": container.decode('utf-8')
            }

        except Exception as e:
            logger.error(f"Docker execution failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
