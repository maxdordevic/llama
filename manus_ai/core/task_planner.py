"""
Intelligent Task Planning System
Breaks down complex user requests into executable subtasks with dependency management
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
import uuid

from .llm_providers import LLMManager, LLMProvider

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SubTask:
    """Individual subtask in execution plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    agent_type: str = "general"  # research, code, web, data, file
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # IDs of dependent tasks
    estimated_duration: int = 60  # seconds
    actual_duration: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan for user request"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str = ""
    subtasks: List[SubTask] = field(default_factory=list)
    execution_strategy: str = "sequential"  # sequential, parallel, mixed
    total_estimated_duration: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_ready_tasks(self) -> List[SubTask]:
        """Get tasks ready for execution (dependencies satisfied)"""
        ready = []
        completed_ids = {t.id for t in self.subtasks if t.status == TaskStatus.COMPLETED}

        for task in self.subtasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if all(dep_id in completed_ids for dep_id in task.dependencies):
                    ready.append(task)

        # Sort by priority
        ready.sort(key=lambda t: t.priority.value, reverse=True)
        return ready

    def get_task_by_id(self, task_id: str) -> Optional[SubTask]:
        """Get task by ID"""
        for task in self.subtasks:
            if task.id == task_id:
                return task
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get execution progress"""
        total = len(self.subtasks)
        if total == 0:
            return {"progress": 0, "completed": 0, "total": 0, "status": "empty"}

        completed = sum(1 for t in self.subtasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.subtasks if t.status == TaskStatus.IN_PROGRESS)
        failed = sum(1 for t in self.subtasks if t.status == TaskStatus.FAILED)

        return {
            "progress": (completed / total) * 100,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "total": total,
            "status": "in_progress" if in_progress > 0 else ("completed" if completed == total else "pending")
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_request": self.user_request,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "execution_strategy": self.execution_strategy,
            "total_estimated_duration": self.total_estimated_duration,
            "created_at": self.created_at.isoformat(),
            "progress": self.get_progress(),
            "metadata": self.metadata,
        }


class TaskPlanner:
    """Intelligent task planning using LLM"""

    PLANNING_PROMPT = """You are an expert AI task planner. Your job is to break down complex user requests into detailed, executable subtasks.

User Request: {user_request}

Analyze this request and create a comprehensive execution plan. Consider:
1. What are the distinct subtasks needed?
2. What are the dependencies between tasks?
3. What type of agent is best suited for each task?
4. Can any tasks be executed in parallel?
5. What is the optimal execution order?

Available agent types:
- research: Web research, information gathering, fact-checking
- code: Code generation, software development, debugging
- web: Web automation, form filling, scraping
- data: Data analysis, visualization, statistical processing
- file: File processing, format conversion, document generation
- general: General purpose tasks

Provide your response in JSON format:
{{
    "analysis": "Brief analysis of the request and approach",
    "execution_strategy": "sequential|parallel|mixed",
    "subtasks": [
        {{
            "title": "Brief task title",
            "description": "Detailed task description",
            "agent_type": "research|code|web|data|file|general",
            "priority": "low|medium|high|critical",
            "dependencies": [],  // List of task indices this depends on
            "estimated_duration": 60  // seconds
        }}
    ]
}}

Be thorough and break complex tasks into manageable steps. Ensure dependencies are correctly identified."""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm_manager = llm_manager or LLMManager()
        self.planning_provider = LLMProvider.CLAUDE_SONNET_4_5  # Best for planning

    async def create_plan(self, user_request: str) -> ExecutionPlan:
        """Create execution plan from user request"""
        logger.info(f"Creating execution plan for: {user_request[:100]}...")

        # Generate plan using LLM
        prompt = self.PLANNING_PROMPT.format(user_request=user_request)
        messages = [
            {"role": "system", "content": "You are an expert task planning AI. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm_manager.generate(
                messages=messages,
                provider=self.planning_provider,
                temperature=0.3,  # Lower temperature for more consistent planning
                max_tokens=4096
            )

            # Parse LLM response
            plan_data = self._parse_plan_response(response["content"])

            # Create execution plan
            plan = ExecutionPlan(
                user_request=user_request,
                execution_strategy=plan_data.get("execution_strategy", "sequential"),
                metadata={"analysis": plan_data.get("analysis", "")}
            )

            # Create subtasks
            subtasks_data = plan_data.get("subtasks", [])
            task_id_map = {}  # Map index to task ID

            for idx, task_data in enumerate(subtasks_data):
                # Create subtask
                subtask = SubTask(
                    title=task_data.get("title", f"Task {idx + 1}"),
                    description=task_data.get("description", ""),
                    agent_type=task_data.get("agent_type", "general"),
                    priority=self._parse_priority(task_data.get("priority", "medium")),
                    estimated_duration=task_data.get("estimated_duration", 60),
                )
                task_id_map[idx] = subtask.id
                plan.subtasks.append(subtask)

            # Resolve dependencies (convert indices to IDs)
            for idx, task_data in enumerate(subtasks_data):
                subtask = plan.subtasks[idx]
                dep_indices = task_data.get("dependencies", [])
                subtask.dependencies = [task_id_map[dep_idx] for dep_idx in dep_indices if dep_idx in task_id_map]

            # Calculate total estimated duration
            plan.total_estimated_duration = sum(t.estimated_duration for t in plan.subtasks)

            logger.info(f"Created plan with {len(plan.subtasks)} subtasks")
            return plan

        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            # Fallback to simple single-task plan
            return self._create_fallback_plan(user_request)

    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into plan data"""
        # Try to extract JSON from response
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan response: {e}")
            # Try to find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except:
                    pass

            raise ValueError("Could not parse plan response as JSON")

    def _parse_priority(self, priority_str: str) -> TaskPriority:
        """Parse priority string to enum"""
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }
        return priority_map.get(priority_str.lower(), TaskPriority.MEDIUM)

    def _create_fallback_plan(self, user_request: str) -> ExecutionPlan:
        """Create simple fallback plan if LLM planning fails"""
        logger.warning("Using fallback plan")

        plan = ExecutionPlan(user_request=user_request)
        plan.subtasks.append(SubTask(
            title="Execute user request",
            description=user_request,
            agent_type="general",
            priority=TaskPriority.HIGH,
            estimated_duration=120
        ))
        plan.total_estimated_duration = 120

        return plan

    async def refine_plan(self, plan: ExecutionPlan, feedback: str) -> ExecutionPlan:
        """Refine execution plan based on feedback or intermediate results"""
        logger.info(f"Refining plan {plan.id} with feedback")

        prompt = f"""You are refining an execution plan based on new information.

Original User Request: {plan.user_request}

Current Plan:
{json.dumps(plan.to_dict(), indent=2)}

Feedback/New Information: {feedback}

Please update the plan to incorporate this feedback. You can:
- Add new subtasks
- Modify existing tasks
- Adjust priorities
- Change execution order
- Update dependencies

Provide the updated plan in the same JSON format as before."""

        messages = [
            {"role": "system", "content": "You are an expert task planning AI. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm_manager.generate(
                messages=messages,
                provider=self.planning_provider,
                temperature=0.3,
                max_tokens=4096
            )

            # Parse and create refined plan
            plan_data = self._parse_plan_response(response["content"])
            # Create new plan (similar to create_plan)
            # ... implementation details ...

            return plan

        except Exception as e:
            logger.error(f"Error refining plan: {e}")
            return plan  # Return original plan if refinement fails

    def estimate_total_time(self, plan: ExecutionPlan) -> int:
        """Estimate total execution time accounting for parallelization"""
        if plan.execution_strategy == "sequential":
            return sum(t.estimated_duration for t in plan.subtasks)

        elif plan.execution_strategy == "parallel":
            # Assume all independent tasks run in parallel
            # Time = longest chain of dependent tasks
            return self._calculate_critical_path(plan)

        else:  # mixed
            # Estimate based on partial parallelization
            return int(plan.total_estimated_duration * 0.7)  # Assume 30% speedup

    def _calculate_critical_path(self, plan: ExecutionPlan) -> int:
        """Calculate critical path (longest chain of dependencies)"""
        # Simple implementation - can be optimized
        task_times = {}

        def get_task_time(task: SubTask) -> int:
            if task.id in task_times:
                return task_times[task.id]

            if not task.dependencies:
                task_times[task.id] = task.estimated_duration
                return task.estimated_duration

            max_dep_time = 0
            for dep_id in task.dependencies:
                dep_task = plan.get_task_by_id(dep_id)
                if dep_task:
                    max_dep_time = max(max_dep_time, get_task_time(dep_task))

            task_times[task.id] = max_dep_time + task.estimated_duration
            return task_times[task.id]

        if not plan.subtasks:
            return 0

        return max(get_task_time(task) for task in plan.subtasks)
