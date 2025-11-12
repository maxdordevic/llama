"""
Agent Orchestrator - Core coordination system for multi-agent execution
Manages task distribution, agent lifecycle, and result aggregation
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid

from .task_planner import TaskPlanner, ExecutionPlan, SubTask, TaskStatus
from .llm_providers import LLMManager, LLMProvider
from ..agents.base_agent import BaseAgent
from ..agents.research_agent import ResearchAgent
from ..agents.code_agent import CodeAgent
from ..agents.web_agent import WebAutomationAgent
from ..agents.data_agent import DataAnalysisAgent
from ..agents.file_agent import FileProcessingAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Core orchestrator managing multi-agent task execution
    Features:
    - Parallel and sequential task execution
    - Agent lifecycle management
    - Progress tracking and reporting
    - Error handling and recovery
    - Result aggregation
    """

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        task_planner: Optional[TaskPlanner] = None,
        max_parallel_tasks: int = 3
    ):
        self.llm_manager = llm_manager or LLMManager()
        self.task_planner = task_planner or TaskPlanner(self.llm_manager)
        self.max_parallel_tasks = max_parallel_tasks

        # Agent registry
        self.agents: Dict[str, type] = {
            "research": ResearchAgent,
            "code": CodeAgent,
            "web": WebAutomationAgent,
            "data": DataAnalysisAgent,
            "file": FileProcessingAgent,
        }

        # Active sessions
        self.sessions: Dict[str, ExecutionPlan] = {}

        # Progress callbacks
        self.progress_callbacks: Dict[str, List[Callable]] = {}

    async def execute_request(
        self,
        user_request: str,
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute complete user request end-to-end

        Args:
            user_request: User's task description
            session_id: Optional session ID for tracking
            progress_callback: Optional callback for progress updates

        Returns:
            Complete execution results
        """
        session_id = session_id or str(uuid.uuid4())
        logger.info(f"[Session {session_id}] Starting execution: {user_request[:100]}...")

        try:
            # Step 1: Create execution plan
            await self._notify_progress(session_id, {
                "stage": "planning",
                "message": "Analyzing request and creating execution plan..."
            })

            plan = await self.task_planner.create_plan(user_request)
            self.sessions[session_id] = plan

            if progress_callback:
                if session_id not in self.progress_callbacks:
                    self.progress_callbacks[session_id] = []
                self.progress_callbacks[session_id].append(progress_callback)

            await self._notify_progress(session_id, {
                "stage": "planning_complete",
                "message": f"Created plan with {len(plan.subtasks)} subtasks",
                "plan": plan.to_dict()
            })

            # Step 2: Execute plan
            await self._notify_progress(session_id, {
                "stage": "execution",
                "message": "Beginning task execution..."
            })

            results = await self._execute_plan(session_id, plan)

            # Step 3: Aggregate results
            await self._notify_progress(session_id, {
                "stage": "aggregation",
                "message": "Aggregating results..."
            })

            final_result = await self._aggregate_results(plan, results)

            # Step 4: Complete
            await self._notify_progress(session_id, {
                "stage": "complete",
                "message": "Task completed successfully",
                "result": final_result
            })

            logger.info(f"[Session {session_id}] Completed successfully")

            return {
                "session_id": session_id,
                "status": "success",
                "user_request": user_request,
                "plan": plan.to_dict(),
                "result": final_result,
                "execution_time": sum(
                    t.actual_duration or 0 for t in plan.subtasks
                ),
            }

        except Exception as e:
            logger.error(f"[Session {session_id}] Execution failed: {e}", exc_info=True)

            await self._notify_progress(session_id, {
                "stage": "error",
                "message": f"Execution failed: {str(e)}",
                "error": str(e)
            })

            return {
                "session_id": session_id,
                "status": "error",
                "user_request": user_request,
                "error": str(e)
            }

    async def _execute_plan(
        self,
        session_id: str,
        plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """Execute execution plan with parallelization"""
        results = {}

        if plan.execution_strategy == "sequential":
            # Sequential execution
            for task in plan.subtasks:
                result = await self._execute_task(session_id, plan, task)
                results[task.id] = result

        elif plan.execution_strategy == "parallel":
            # Full parallel execution (respecting dependencies)
            await self._execute_parallel(session_id, plan, results)

        else:  # mixed
            # Mixed strategy: parallelize where possible
            await self._execute_parallel(session_id, plan, results)

        return results

    async def _execute_parallel(
        self,
        session_id: str,
        plan: ExecutionPlan,
        results: Dict[str, Any]
    ):
        """Execute tasks in parallel respecting dependencies"""
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)

        async def execute_with_semaphore(task: SubTask):
            async with semaphore:
                return await self._execute_task(session_id, plan, task)

        while True:
            # Get tasks ready for execution
            ready_tasks = plan.get_ready_tasks()

            if not ready_tasks:
                # Check if all tasks are complete
                if all(t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for t in plan.subtasks):
                    break
                # Wait a bit and check again
                await asyncio.sleep(0.5)
                continue

            # Execute ready tasks in parallel
            tasks = [execute_with_semaphore(task) for task in ready_tasks]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for task, result in zip(ready_tasks, task_results):
                if isinstance(result, Exception):
                    results[task.id] = {"error": str(result)}
                else:
                    results[task.id] = result

    async def _execute_task(
        self,
        session_id: str,
        plan: ExecutionPlan,
        task: SubTask
    ) -> Dict[str, Any]:
        """Execute single subtask"""
        logger.info(f"[Session {session_id}] Executing task: {task.title}")

        # Update task status
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()

        await self._notify_progress(session_id, {
            "stage": "task_started",
            "task": task.to_dict()
        })

        try:
            # Get appropriate agent
            agent = await self._get_agent(task.agent_type)

            # Execute task
            result = await agent.execute(
                task=task,
                context={
                    "session_id": session_id,
                    "plan": plan,
                    "llm_manager": self.llm_manager
                }
            )

            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.actual_duration = int((task.completed_at - task.started_at).total_seconds())
            task.result = result

            await self._notify_progress(session_id, {
                "stage": "task_completed",
                "task": task.to_dict(),
                "progress": plan.get_progress()
            })

            logger.info(f"[Session {session_id}] Task completed: {task.title}")

            return result

        except Exception as e:
            logger.error(f"[Session {session_id}] Task failed: {task.title} - {e}", exc_info=True)

            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.actual_duration = int((task.completed_at - task.started_at).total_seconds())
            task.error = str(e)

            await self._notify_progress(session_id, {
                "stage": "task_failed",
                "task": task.to_dict(),
                "error": str(e)
            })

            # Decide whether to continue or abort
            if task.priority.value >= 3:  # HIGH or CRITICAL
                raise  # Abort execution

            return {"error": str(e)}

    async def _get_agent(self, agent_type: str) -> BaseAgent:
        """Get agent instance for task"""
        agent_class = self.agents.get(agent_type)

        if not agent_class:
            # Fallback to general agent
            logger.warning(f"Unknown agent type: {agent_type}, using general agent")
            from ..agents.general_agent import GeneralAgent
            agent_class = GeneralAgent

        # Create agent instance
        return agent_class(llm_manager=self.llm_manager)

    async def _aggregate_results(
        self,
        plan: ExecutionPlan,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate results from all subtasks into final output"""
        logger.info("Aggregating results from all subtasks")

        # Collect successful results
        successful_results = []
        failed_tasks = []

        for task in plan.subtasks:
            if task.status == TaskStatus.COMPLETED and task.result:
                successful_results.append({
                    "task": task.title,
                    "result": task.result
                })
            elif task.status == TaskStatus.FAILED:
                failed_tasks.append({
                    "task": task.title,
                    "error": task.error
                })

        # Use LLM to synthesize final response
        synthesis_prompt = f"""You are synthesizing the final result for a user request that was broken down into subtasks.

Original User Request: {plan.user_request}

Subtask Results:
{self._format_results(successful_results)}

Failed Tasks:
{self._format_failures(failed_tasks)}

Please provide a comprehensive, user-friendly response that:
1. Directly addresses the user's original request
2. Integrates information from all successful subtasks
3. Presents the results in a clear, organized manner
4. Notes any limitations due to failed tasks (if any)
5. Provides actionable next steps or recommendations

Your response should be complete and ready to present to the user."""

        messages = [
            {"role": "system", "content": "You are a helpful AI assistant synthesizing task results."},
            {"role": "user", "content": synthesis_prompt}
        ]

        try:
            response = await self.llm_manager.generate(
                messages=messages,
                provider=LLMProvider.CLAUDE_SONNET_4_5,
                temperature=0.5,
                max_tokens=4096
            )

            return {
                "summary": response["content"],
                "subtask_results": successful_results,
                "failed_tasks": failed_tasks,
                "metadata": {
                    "total_tasks": len(plan.subtasks),
                    "successful": len(successful_results),
                    "failed": len(failed_tasks)
                }
            }

        except Exception as e:
            logger.error(f"Error aggregating results: {e}")
            # Fallback to simple aggregation
            return {
                "summary": "Task execution completed. See subtask results for details.",
                "subtask_results": successful_results,
                "failed_tasks": failed_tasks
            }

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format results for LLM consumption"""
        if not results:
            return "No successful results"

        formatted = []
        for idx, item in enumerate(results, 1):
            formatted.append(f"{idx}. {item['task']}")
            formatted.append(f"   Result: {item['result']}")

        return "\n".join(formatted)

    def _format_failures(self, failures: List[Dict[str, Any]]) -> str:
        """Format failures for LLM consumption"""
        if not failures:
            return "No failures"

        formatted = []
        for idx, item in enumerate(failures, 1):
            formatted.append(f"{idx}. {item['task']}")
            formatted.append(f"   Error: {item['error']}")

        return "\n".join(formatted)

    async def _notify_progress(self, session_id: str, update: Dict[str, Any]):
        """Notify progress callbacks"""
        update["timestamp"] = datetime.utcnow().isoformat()
        update["session_id"] = session_id

        if session_id in self.progress_callbacks:
            for callback in self.progress_callbacks[session_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(update)
                    else:
                        callback(update)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")

    def get_session(self, session_id: str) -> Optional[ExecutionPlan]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    async def pause_session(self, session_id: str):
        """Pause session execution"""
        # Implementation for pausing execution
        logger.info(f"Pausing session {session_id}")
        # TODO: Implement pause logic

    async def resume_session(self, session_id: str):
        """Resume paused session"""
        # Implementation for resuming execution
        logger.info(f"Resuming session {session_id}")
        # TODO: Implement resume logic

    async def cancel_session(self, session_id: str):
        """Cancel session execution"""
        logger.info(f"Cancelling session {session_id}")
        if session_id in self.sessions:
            plan = self.sessions[session_id]
            for task in plan.subtasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    task.status = TaskStatus.FAILED
                    task.error = "Cancelled by user"
