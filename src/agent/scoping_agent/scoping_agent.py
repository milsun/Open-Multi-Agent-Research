from __future__ import annotations

"""Scoping agent – first step in the DeepResearch pipeline.

This agent follows the standard AsyncMultiStepAgent pattern and uses natural
conversation flow with tool discovery rather than hardcoded phases.

Responsibilities
----------------
1. Receive the user's natural-language research request.
2. Decide whether a clarifying question is required and – if so – ask it via tools.
3. Produce a structured research plan using available tools.
4. Present the plan back to the user and get confirmation via tools.
5. Once confirmed, pass control to the planning agent for execution.

The agent uses the standard ReAct framework with tool calling rather than
hardcoded phase methods.
"""

from typing import Any, Dict, List, Optional
import asyncio

from src.models import Model
from src.logger import logger
from src.registry import AGENT
from src.agent.general_agent import GeneralAgent
from src.base.async_multistep_agent import PromptTemplates


@AGENT.register_module(name="scoping_agent", force=True)
class ScopingAgent(GeneralAgent):
    """
    Interactive scoping agent that follows standard agentic patterns.
    
    Uses the AsyncMultiStepAgent ReAct framework with natural conversation flow
    and tool discovery to handle research scoping and planning.
    """

    def __init__(
        self,
        config,
        tools: list[Any],
        model: Model,
        prompt_templates: PromptTemplates | None = None,
        planning_interval: int | None = None,
        stream_outputs: bool = False,
        max_tool_threads: int | None = None,
        **kwargs,
    ):
        super().__init__(
            config=config,
            tools=tools,
            model=model,
            prompt_templates=prompt_templates,
            planning_interval=planning_interval,
            stream_outputs=stream_outputs,
            max_tool_threads=max_tool_threads,
            **kwargs,
        )
        
        # Store scoping state in agent state for tool access
        self.state.update({
            "scoping_phase": "initial",
            "clarifications_collected": [],
            "research_plan": None,
            "plan_approved": False,
            "ready_for_handoff": False
        })

    async def run(
        self,
        task: str,
        stream: bool = False,
        reset: bool = True,
        images: list["PIL.Image.Image"] | None = None,
        additional_args: dict | None = None,
        max_steps: int | None = None,
    ) -> Any:
        """
        Run the scoping agent using the standard AsyncMultiStepAgent pattern.
        
        The agent will use natural conversation flow with tools to:
        1. Analyze the request and ask clarifications if needed
        2. Develop a research plan 
        3. Present plan for confirmation
        4. Prepare handoff to planning agent
        """
        # Store the original task in state for tools to access
        self.state["original_task"] = task
        self.state["current_task"] = task
        
        # Use the parent's run method with the task (task_instruction will handle proper formatting)
        return await super().run(
            task=task,
            stream=stream,
            reset=reset,
            images=images,
            additional_args=additional_args,
            max_steps=max_steps or 10  # Limit steps for scoping phase
        ) 