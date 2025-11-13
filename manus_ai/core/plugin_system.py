"""
Plugin System for Custom Agent Extensibility
Allows dynamic loading and registration of custom agents
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Plugin status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    capabilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class PluginInfo:
    """Plugin information"""
    metadata: PluginMetadata
    plugin_id: str
    status: PluginStatus
    file_path: str
    class_name: str
    instance: Optional[Any] = None
    error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents (built-in and custom)"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.description = ""
        self.capabilities = []
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent task

        Args:
            task: Task dictionary with parameters

        Returns:
            Result dictionary
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities
        }

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize agent with configuration

        Args:
            config: Configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        return True

    async def cleanup(self):
        """Cleanup resources"""
        pass

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate task parameters

        Args:
            task: Task dictionary

        Returns:
            True if valid, False otherwise
        """
        return True


class PluginManager:
    """Manages plugin lifecycle and registration"""

    def __init__(self, plugin_dir: str = "plugins"):
        """
        Initialize plugin manager

        Args:
            plugin_dir: Directory containing plugins
        """
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, PluginInfo] = {}
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger(__name__)

        # Create plugin directory if it doesn't exist
        self.plugin_dir.mkdir(exist_ok=True)

        # Add plugin dir to Python path
        if str(self.plugin_dir.absolute()) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir.absolute()))

    async def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in plugin directory

        Returns:
            List of plugin IDs
        """
        discovered = []

        # Look for Python files in plugin directory
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            plugin_id = file_path.stem
            self.logger.info(f"Discovered plugin: {plugin_id}")
            discovered.append(plugin_id)

        return discovered

    async def load_plugin(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load a plugin

        Args:
            plugin_id: Plugin identifier
            config: Optional configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Loading plugin: {plugin_id}")

            # Find plugin file
            plugin_file = self.plugin_dir / f"{plugin_id}.py"
            if not plugin_file.exists():
                raise FileNotFoundError(f"Plugin file not found: {plugin_file}")

            # Import module
            spec = importlib.util.spec_from_file_location(plugin_id, plugin_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load plugin: {plugin_id}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find agent class (should inherit from BaseAgent)
            agent_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseAgent) and obj != BaseAgent:
                    agent_class = obj
                    break

            if agent_class is None:
                raise ValueError(f"No agent class found in plugin: {plugin_id}")

            # Get plugin metadata
            metadata = self._extract_metadata(module, agent_class)

            # Create plugin info
            plugin_info = PluginInfo(
                metadata=metadata,
                plugin_id=plugin_id,
                status=PluginStatus.LOADING,
                file_path=str(plugin_file),
                class_name=agent_class.__name__,
                config=config or {}
            )

            # Instantiate agent
            agent_instance = agent_class()

            # Initialize with config
            if not await agent_instance.initialize(plugin_info.config):
                raise Exception("Agent initialization failed")

            plugin_info.instance = agent_instance
            plugin_info.status = PluginStatus.ENABLED

            # Register
            self.plugins[plugin_id] = plugin_info
            self.agents[metadata.name] = agent_instance

            self.logger.info(f"Successfully loaded plugin: {plugin_id} ({metadata.name})")
            return True

        except Exception as e:
            error_msg = f"Failed to load plugin {plugin_id}: {e}"
            self.logger.error(error_msg)

            # Store error info
            if plugin_id in self.plugins:
                self.plugins[plugin_id].status = PluginStatus.ERROR
                self.plugins[plugin_id].error = str(e)
            else:
                self.plugins[plugin_id] = PluginInfo(
                    metadata=PluginMetadata(
                        name=plugin_id,
                        version="unknown",
                        author="unknown",
                        description="Failed to load",
                        capabilities=[]
                    ),
                    plugin_id=plugin_id,
                    status=PluginStatus.ERROR,
                    file_path=str(self.plugin_dir / f"{plugin_id}.py"),
                    class_name="unknown",
                    error=str(e)
                )

            return False

    def _extract_metadata(self, module, agent_class) -> PluginMetadata:
        """Extract plugin metadata from module and class"""
        # Try to get metadata from module variable
        if hasattr(module, "PLUGIN_METADATA"):
            meta_dict = module.PLUGIN_METADATA
            return PluginMetadata(**meta_dict)

        # Otherwise, extract from docstring and attributes
        doc = inspect.getdoc(agent_class) or agent_class.__name__
        instance = agent_class()

        return PluginMetadata(
            name=getattr(instance, "name", agent_class.__name__),
            version=getattr(module, "__version__", "1.0.0"),
            author=getattr(module, "__author__", "Unknown"),
            description=getattr(instance, "description", doc),
            capabilities=getattr(instance, "capabilities", []),
            dependencies=getattr(module, "__dependencies__", []),
            tags=getattr(module, "__tags__", [])
        )

    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if successful
        """
        if plugin_id not in self.plugins:
            self.logger.warning(f"Plugin not loaded: {plugin_id}")
            return False

        try:
            plugin_info = self.plugins[plugin_id]

            # Cleanup agent
            if plugin_info.instance:
                await plugin_info.instance.cleanup()

            # Remove from registries
            if plugin_info.metadata.name in self.agents:
                del self.agents[plugin_info.metadata.name]

            del self.plugins[plugin_id]

            self.logger.info(f"Unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False

    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if successful
        """
        config = None
        if plugin_id in self.plugins:
            config = self.plugins[plugin_id].config
            await self.unload_plugin(plugin_id)

        return await self.load_plugin(plugin_id, config)

    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a disabled plugin"""
        if plugin_id not in self.plugins:
            return await self.load_plugin(plugin_id)

        plugin_info = self.plugins[plugin_id]
        if plugin_info.status == PluginStatus.ENABLED:
            return True

        plugin_info.status = PluginStatus.ENABLED
        return True

    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin without unloading"""
        if plugin_id not in self.plugins:
            return False

        self.plugins[plugin_id].status = PluginStatus.DISABLED
        return True

    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin info"""
        return self.plugins.get(plugin_id)

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent instance by name"""
        return self.agents.get(agent_name)

    def list_plugins(self, status_filter: Optional[PluginStatus] = None) -> List[PluginInfo]:
        """
        List all plugins

        Args:
            status_filter: Optional status filter

        Returns:
            List of plugin info
        """
        plugins = list(self.plugins.values())

        if status_filter:
            plugins = [p for p in plugins if p.status == status_filter]

        return plugins

    def list_agents(self, enabled_only: bool = True) -> Dict[str, BaseAgent]:
        """
        List all agents

        Args:
            enabled_only: Only return enabled agents

        Returns:
            Dictionary of agent name to instance
        """
        if not enabled_only:
            return self.agents

        return {
            name: agent
            for name, agent in self.agents.items()
            if any(p.metadata.name == name and p.status == PluginStatus.ENABLED
                   for p in self.plugins.values())
        }

    async def execute_agent(
        self,
        agent_name: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent task

        Args:
            agent_name: Name of agent to execute
            task: Task parameters

        Returns:
            Task result
        """
        agent = self.get_agent(agent_name)
        if not agent:
            return {
                "status": "error",
                "error": f"Agent not found: {agent_name}",
                "agent": agent_name
            }

        # Check if plugin is enabled
        plugin_info = next(
            (p for p in self.plugins.values() if p.metadata.name == agent_name),
            None
        )

        if plugin_info and plugin_info.status != PluginStatus.ENABLED:
            return {
                "status": "error",
                "error": f"Agent is disabled: {agent_name}",
                "agent": agent_name
            }

        # Validate task
        if not agent.validate_task(task):
            return {
                "status": "error",
                "error": "Invalid task parameters",
                "agent": agent_name
            }

        # Execute
        try:
            result = await agent.execute(task)
            return result
        except Exception as e:
            self.logger.error(f"Agent execution failed for {agent_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent": agent_name
            }

    def create_plugin_template(self, plugin_id: str) -> str:
        """
        Create a plugin template file

        Args:
            plugin_id: Plugin identifier

        Returns:
            Path to created template
        """
        template = '''"""
Custom Agent Plugin: {plugin_id}
"""

from manus_ai.core.plugin_system import BaseAgent
from typing import Dict, Any

__version__ = "1.0.0"
__author__ = "Your Name"
__dependencies__ = []
__tags__ = ["custom"]

PLUGIN_METADATA = {{
    "name": "{plugin_id}",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Description of what this agent does",
    "capabilities": [
        "Capability 1",
        "Capability 2"
    ],
    "dependencies": [],
    "tags": ["custom"]
}}


class {class_name}(BaseAgent):
    """Custom agent implementation"""

    def __init__(self):
        super().__init__()
        self.name = "{plugin_id}"
        self.description = "Description of what this agent does"
        self.capabilities = [
            "Capability 1",
            "Capability 2"
        ]

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize agent with configuration"""
        self.logger.info(f"Initializing {{self.name}} with config: {{config}}")
        # Add your initialization logic here
        return True

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent task

        Args:
            task: Task parameters (e.g., {{"input": "...", "param1": "..."}})

        Returns:
            Result dictionary
        """
        try:
            # Add your agent logic here
            input_data = task.get("input", "")

            # Example processing
            result = f"Processed: {{input_data}}"

            return {{
                "status": "success",
                "agent": self.name,
                "result": result,
                "message": "Task completed successfully"
            }}

        except Exception as e:
            self.logger.error(f"Execution failed: {{e}}")
            return {{
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "message": f"Task failed: {{e}}"
            }}

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task parameters"""
        # Add validation logic
        return "input" in task

    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info(f"Cleaning up {{self.name}}")
        # Add cleanup logic here
'''

        class_name = "".join(word.capitalize() for word in plugin_id.split("_"))
        content = template.format(plugin_id=plugin_id, class_name=class_name)

        file_path = self.plugin_dir / f"{plugin_id}.py"
        file_path.write_text(content)

        self.logger.info(f"Created plugin template: {file_path}")
        return str(file_path)

    def export_plugin_catalog(self) -> str:
        """Export plugin catalog as JSON"""
        catalog = []

        for plugin_info in self.plugins.values():
            catalog.append({
                "plugin_id": plugin_info.plugin_id,
                "name": plugin_info.metadata.name,
                "version": plugin_info.metadata.version,
                "author": plugin_info.metadata.author,
                "description": plugin_info.metadata.description,
                "capabilities": plugin_info.metadata.capabilities,
                "dependencies": plugin_info.metadata.dependencies,
                "tags": plugin_info.metadata.tags,
                "status": plugin_info.status.value,
                "class_name": plugin_info.class_name,
                "error": plugin_info.error
            })

        return json.dumps(catalog, indent=2)


# Global plugin manager instance
_plugin_manager_instance: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance"""
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance
