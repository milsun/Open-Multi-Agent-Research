"""
Interactive Planning Tool for user confirmation and plan refinement
"""

import json
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel

from src.tools import AsyncTool, ToolResult
from src.registry import TOOL

@TOOL.register_module(name="interactive_planning_tool", force=True)
class InteractivePlanningTool(AsyncTool):
    """
    Tool for interactive planning that allows presenting research plans to users
    and getting confirmation before execution.
    """
    
    name = "interactive_planning_tool"
    description = "Present research plans to users and get confirmation before execution"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["present_plan"],
                "description": "Present research plan in conversational format and collect user response"
            },
            "content": {
                "type": "string",
                "description": "Conversational explanation of the research plan in natural, flowing language"
            }
        },
        "required": ["action", "content"]
    }
    output_type = "any"

    def __init__(self):
        super().__init__()
        self.console = Console()

    async def forward(self, action: str, content: str) -> ToolResult:
        """Execute the interactive planning action"""
        try:
            if action == "present_plan":
                return self._present_plan(content)
            else:
                return ToolResult(
                    output="",
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            return ToolResult(
                output="",
                error=f"Interactive planning error: {str(e)}"
            )

    def _present_plan(self, plan_content: str) -> ToolResult:
        """Present the research plan to the user in conversational style"""
        self.console.print()
        
        # Present the plan in a clean panel
        panel = Panel(
            f"[white]{plan_content}[/white]",
            title="[bold blue]🔍 Research Plan[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
        
        # Simple confirmation request
        self.console.print(f"[bold green]What do you think of this research plan?[/bold green]")
        self.console.print(f"[dim]Feel free to approve it, suggest changes, or ask me to try a different approach.[/dim]")
        self.console.print()
        
        self.console.print(f"[bold]Your response: [/bold]", end="")
        
        response = input().strip()
        
        if not response:
            self.console.print(f"\n[yellow]I didn't catch that. Could you let me know your thoughts on the plan?[/yellow]")
            self.console.print(f"[bold]Your response: [/bold]", end="")
            response = input().strip()
            
            if not response:
                response = "No response provided"
                
        # Return the raw user response - let the scoping agent handle interpretation
        return ToolResult(
            output=response,
            error=None
        )


@TOOL.register_module(name="user_clarification_tool", force=True)
class UserClarificationTool(AsyncTool):
    """
    Simplified tool for asking single clarifying questions
    """
    
    name = "user_clarification_tool"
    description = "Ask the user a specific clarifying question to refine the research task"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The clarifying question to ask the user"
            },
            "context": {
                "type": "string", 
                "description": "Optional context about why this clarification is needed",
                "nullable": True
            }
        },
        "required": ["question"]
    }
    output_type = "any"

    def __init__(self):
        super().__init__()
        self.console = Console()

    async def forward(self, question: str, context: str = "") -> ToolResult:
        """Ask a clarifying question and get user response"""
        try:
            self.console.print()
            
            # Create the clarification panel
            content = f"[yellow]🤔 {question}[/yellow]"
            if context:
                content += f"\n\n[dim]{context}[/dim]"
            
            panel = Panel(
                content,
                title="[bold blue]Clarification Needed[/bold blue]",
                border_style="blue",
                padding=(1, 2)
            )
            
            self.console.print(panel)
            self.console.print(f"[bold green]Your response: [/bold green]", end="")
            
            user_response = input().strip()
            
            if not user_response:
                self.console.print(f"\n[yellow]Could you provide some input to help me understand what you need?[/yellow]")
                self.console.print(f"[bold green]Your response: [/bold green]", end="")
                user_response = input().strip()
                
                if not user_response:
                    user_response = "No response provided"
                        
            return ToolResult(
                output=user_response,
                error=None
            )
            
        except Exception as e:
            return ToolResult(
                output="",
                error=f"Clarification error: {str(e)}"
            )