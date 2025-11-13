"""
Workflow Templates and Task Patterns
Allows saving and reusing common multi-step workflows
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Types of workflow steps"""
    AGENT_EXECUTION = "agent_execution"
    LLM_QUERY = "llm_query"
    DATA_TRANSFORM = "data_transform"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"
    WEBHOOK = "webhook"
    WAIT = "wait"


@dataclass
class WorkflowStep:
    """Individual workflow step"""
    step_id: str
    step_type: StepType
    name: str
    description: str
    agent_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    retry_on_failure: bool = False
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    condition: Optional[str] = None  # For conditional steps


@dataclass
class WorkflowTemplate:
    """Workflow template definition"""
    template_id: str
    name: str
    description: str
    category: str
    tags: List[str]
    steps: List[WorkflowStep]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    author: str
    version: str = "1.0.0"
    is_public: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Running workflow instance"""
    execution_id: str
    template_id: str
    workflow_name: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_errors: Dict[str, str] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class WorkflowEngine:
    """Executes workflow templates"""

    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Initialize workflow engine

        Args:
            orchestrator: Optional orchestrator for agent execution
        """
        self.orchestrator = orchestrator
        self.executions: Dict[str, WorkflowExecution] = {}
        self.logger = logging.getLogger(__name__)

    async def execute_workflow(
        self,
        template: WorkflowTemplate,
        input_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow template

        Args:
            template: Workflow template to execute
            input_data: Input data for the workflow
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            Workflow execution result
        """
        # Create execution
        execution_id = f"exec_{int(datetime.utcnow().timestamp())}_{template.template_id}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            template_id=template.template_id,
            workflow_name=template.name,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
            input_data=input_data,
            user_id=user_id,
            session_id=session_id
        )

        self.executions[execution_id] = execution
        self.logger.info(f"Starting workflow execution: {execution_id}")

        try:
            # Build dependency graph
            step_map = {step.step_id: step for step in template.steps}

            # Execute steps in topological order
            executed = set()
            while len(executed) < len(template.steps):
                # Find steps ready to execute
                ready_steps = [
                    step for step in template.steps
                    if step.step_id not in executed and
                    all(dep in executed for dep in step.depends_on)
                ]

                if not ready_steps:
                    # Check for circular dependencies
                    remaining = [s for s in template.steps if s.step_id not in executed]
                    raise ValueError(f"Circular dependency or missing dependencies: {[s.step_id for s in remaining]}")

                # Execute ready steps (can be parallel)
                await self._execute_steps_parallel(execution, ready_steps, input_data)

                # Mark as executed
                for step in ready_steps:
                    executed.add(step.step_id)

            # Workflow completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.output_data = execution.step_results

            self.logger.info(f"Workflow completed: {execution_id}")

        except Exception as e:
            self.logger.error(f"Workflow failed: {execution_id} - {e}")
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.output_data = {"error": str(e)}

        return execution

    async def _execute_steps_parallel(
        self,
        execution: WorkflowExecution,
        steps: List[WorkflowStep],
        context: Dict[str, Any]
    ):
        """Execute multiple steps in parallel"""
        tasks = []
        for step in steps:
            tasks.append(self._execute_step(execution, step, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                execution.step_errors[step.step_id] = str(result)
                if not step.retry_on_failure:
                    raise result
            else:
                execution.step_results[step.step_id] = result

    async def _execute_step(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single workflow step"""
        execution.current_step = step.step_id
        self.logger.info(f"Executing step: {step.step_id} ({step.step_type.value})")

        # Resolve parameters with context
        parameters = self._resolve_parameters(step.parameters, context, execution.step_results)

        # Execute based on step type
        if step.step_type == StepType.AGENT_EXECUTION:
            return await self._execute_agent_step(step, parameters)
        elif step.step_type == StepType.LLM_QUERY:
            return await self._execute_llm_step(step, parameters)
        elif step.step_type == StepType.DATA_TRANSFORM:
            return await self._execute_transform_step(step, parameters)
        elif step.step_type == StepType.CONDITIONAL:
            return await self._execute_conditional_step(step, parameters, context, execution)
        elif step.step_type == StepType.WAIT:
            await asyncio.sleep(parameters.get("seconds", 1))
            return {"waited": parameters.get("seconds", 1)}
        else:
            raise ValueError(f"Unsupported step type: {step.step_type}")

    def _resolve_parameters(
        self,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter references to actual values"""
        resolved = {}

        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to context or previous step result
                # Format: $input.field or $step_id.field
                parts = value[1:].split(".", 1)
                source = parts[0]

                if source == "input":
                    resolved[key] = context.get(parts[1] if len(parts) > 1 else source)
                elif source in step_results:
                    if len(parts) > 1:
                        resolved[key] = step_results[source].get(parts[1])
                    else:
                        resolved[key] = step_results[source]
                else:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    async def _execute_agent_step(self, step: WorkflowStep, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent step"""
        if not self.orchestrator:
            raise ValueError("Orchestrator not configured")

        # Execute agent
        result = await self.orchestrator.execute_agent(
            agent_name=step.agent_name,
            task=parameters
        )

        return result

    async def _execute_llm_step(self, step: WorkflowStep, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM query step"""
        # Placeholder - would integrate with LLM manager
        return {"response": "LLM response"}

    async def _execute_transform_step(self, step: WorkflowStep, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation step"""
        # Apply transformation function
        transform_func = parameters.get("function")
        input_data = parameters.get("input")

        if transform_func == "extract_field":
            return {parameters.get("output_key", "result"): input_data.get(parameters.get("field"))}
        elif transform_func == "combine":
            return {"result": " ".join(str(v) for v in input_data.values())}
        else:
            return input_data

    async def _execute_conditional_step(
        self,
        step: WorkflowStep,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute conditional step"""
        condition = step.condition
        if not condition:
            return {"executed": False}

        # Simple condition evaluation (extend as needed)
        # Format: "$step_id.field == value"
        if "==" in condition:
            left, right = condition.split("==")
            left_val = self._resolve_parameters({"val": left.strip()}, context, execution.step_results)["val"]
            right_val = right.strip().strip('"\'')
            result = str(left_val) == right_val
        else:
            result = True

        return {"condition_met": result}

    async def pause_workflow(self, execution_id: str):
        """Pause workflow execution"""
        if execution_id in self.executions:
            self.executions[execution_id].status = WorkflowStatus.PAUSED

    async def resume_workflow(self, execution_id: str):
        """Resume paused workflow"""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            if execution.status == WorkflowStatus.PAUSED:
                execution.status = WorkflowStatus.RUNNING
                # Continue execution from current step

    async def cancel_workflow(self, execution_id: str):
        """Cancel workflow execution"""
        if execution_id in self.executions:
            self.executions[execution_id].status = WorkflowStatus.CANCELLED

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.executions.get(execution_id)


class WorkflowLibrary:
    """Manages workflow templates"""

    def __init__(self, storage_dir: str = "workflows"):
        """
        Initialize workflow library

        Args:
            storage_dir: Directory to store templates
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.logger = logging.getLogger(__name__)

    def create_template(
        self,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        category: str = "general",
        tags: Optional[List[str]] = None,
        author: str = "system",
        is_public: bool = False
    ) -> WorkflowTemplate:
        """Create a new workflow template"""
        template_id = f"wf_{int(datetime.utcnow().timestamp())}_{name.lower().replace(' ', '_')}"

        template = WorkflowTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            steps=steps,
            input_schema={},
            output_schema={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            author=author,
            is_public=is_public
        )

        self.templates[template_id] = template
        self._save_template(template)

        self.logger.info(f"Created workflow template: {template_id}")
        return template

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get workflow template by ID"""
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        public_only: bool = False
    ) -> List[WorkflowTemplate]:
        """List workflow templates with optional filters"""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        if public_only:
            templates = [t for t in templates if t.is_public]

        return templates

    def update_template(self, template_id: str, **updates) -> bool:
        """Update workflow template"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()
        self._save_template(template)

        return True

    def delete_template(self, template_id: str) -> bool:
        """Delete workflow template"""
        if template_id in self.templates:
            del self.templates[template_id]
            template_file = self.storage_dir / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            return True
        return False

    def _save_template(self, template: WorkflowTemplate):
        """Save template to disk"""
        template_file = self.storage_dir / f"{template.template_id}.json"

        # Convert to dict
        data = asdict(template)
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()

        with open(template_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_templates(self):
        """Load all templates from disk"""
        for template_file in self.storage_dir.glob("*.json"):
            try:
                with open(template_file) as f:
                    data = json.load(f)

                # Convert dates
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

                # Convert steps
                data["steps"] = [WorkflowStep(**step) for step in data["steps"]]

                template = WorkflowTemplate(**data)
                self.templates[template.template_id] = template

            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")

    def create_builtin_templates(self):
        """Create built-in workflow templates"""
        # Template 1: Research and Summarize
        self.create_template(
            name="Research and Summarize",
            description="Research a topic and create a summary with citations",
            category="research",
            tags=["research", "summary", "citations"],
            is_public=True,
            steps=[
                WorkflowStep(
                    step_id="research",
                    step_type=StepType.AGENT_EXECUTION,
                    name="Research Topic",
                    description="Conduct web research on the topic",
                    agent_name="ResearchAgent",
                    parameters={"query": "$input.topic", "max_sources": 5}
                ),
                WorkflowStep(
                    step_id="summarize",
                    step_type=StepType.AGENT_EXECUTION,
                    name="Create Summary",
                    description="Summarize research findings",
                    agent_name="GeneralAgent",
                    parameters={
                        "task": "summarize",
                        "input": "$research.result",
                        "max_length": 500
                    },
                    depends_on=["research"]
                )
            ]
        )

        # Template 2: Code Generation and Testing
        self.create_template(
            name="Code Generation and Testing",
            description="Generate code and run tests",
            category="development",
            tags=["code", "testing", "development"],
            is_public=True,
            steps=[
                WorkflowStep(
                    step_id="generate_code",
                    step_type=StepType.AGENT_EXECUTION,
                    name="Generate Code",
                    description="Generate code based on specification",
                    agent_name="CodeAgent",
                    parameters={
                        "task": "generate",
                        "specification": "$input.spec",
                        "language": "$input.language"
                    }
                ),
                WorkflowStep(
                    step_id="run_tests",
                    step_type=StepType.AGENT_EXECUTION,
                    name="Run Tests",
                    description="Execute tests on generated code",
                    agent_name="CodeAgent",
                    parameters={
                        "task": "test",
                        "code": "$generate_code.code"
                    },
                    depends_on=["generate_code"]
                )
            ]
        )

        self.logger.info("Created built-in workflow templates")


# Global workflow library instance
_workflow_library_instance: Optional[WorkflowLibrary] = None


def get_workflow_library() -> WorkflowLibrary:
    """Get global workflow library instance"""
    global _workflow_library_instance
    if _workflow_library_instance is None:
        _workflow_library_instance = WorkflowLibrary()
        _workflow_library_instance.load_templates()
        _workflow_library_instance.create_builtin_templates()
    return _workflow_library_instance
