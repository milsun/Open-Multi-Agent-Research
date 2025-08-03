from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.columns import Columns
from rich.align import Align
from dataclasses import dataclass, field
import time

@dataclass
class TokenUsage:
    """
    Contains the token usage information for a given step or run.
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int = field(init=False)

    def __post_init__(self):
        self.total_tokens = self.input_tokens + self.output_tokens

    def dict(self):
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class Timing:
    """
    Contains the timing information for a given step or run.
    """

    start_time: float
    end_time: float | None = None

    @property
    def duration(self):
        return None if self.end_time is None else self.end_time - self.start_time

    def dict(self):
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
        }

    def __repr__(self) -> str:
        return f"Timing(start_time={self.start_time}, end_time={self.end_time}, duration={self.duration})"

class Monitor:
    def __init__(self, tracked_model, logger):
        self.step_durations = []
        self.tracked_model = tracked_model
        self.logger = logger
        self.total_input_token_count = 0
        self.total_output_token_count = 0
        self.current_step = 0
        self.console = Console()
        
        # Progress tracking
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True
        )
        
        # Tool usage tracking
        self.tool_usage = {}
        self.active_tools = set()

    def get_total_token_counts(self) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.total_input_token_count,
            output_tokens=self.total_output_token_count,
        )

    def reset(self):
        self.step_durations = []
        self.total_input_token_count = 0
        self.total_output_token_count = 0
        self.current_step = 0
        self.tool_usage = {}
        self.active_tools = set()

    def start_tool_execution(self, tool_name: str):
        """Start tracking a tool execution"""
        self.active_tools.add(tool_name)
        if tool_name not in self.tool_usage:
            self.tool_usage[tool_name] = {"calls": 0, "total_time": 0}
        self.tool_usage[tool_name]["calls"] += 1
        
        # Show tool execution start (always show in non-debug mode)
        from src.utils.debug_config import is_debug_mode
        if not is_debug_mode():
            self.logger.log(
                Panel(
                    f"🛠️  [bold cyan]Executing Tool:[/bold cyan] [bold yellow]{tool_name}[/bold yellow]",
                    border_style="cyan",
                    padding=(0, 1)
                ),
                level=1
            )

    def end_tool_execution(self, tool_name: str, duration: float):
        """End tracking a tool execution"""
        self.active_tools.discard(tool_name)
        if tool_name in self.tool_usage:
            self.tool_usage[tool_name]["total_time"] += duration
        
        # Tool completion messages are now hidden - only execution start is shown

    def show_agent_status(self, agent_name: str, status: str, step_info: str = ""):
        """Show current agent status with visual indicators"""
        status_icons = {
            "thinking": "🧠",
            "planning": "📋", 
            "searching": "🔍",
            "analyzing": "📊",
            "executing": "⚡",
            "completed": "✅",
            "error": "❌"
        }
        
        icon = status_icons.get(status, "🤖")
        color = {
            "thinking": "blue",
            "planning": "cyan", 
            "searching": "yellow",
            "analyzing": "magenta",
            "executing": "green",
            "completed": "green",
            "error": "red"
        }.get(status, "white")
        
        status_text = f"{icon} [bold {color}]{agent_name}[/bold {color}] - {status.title()}"
        if step_info:
            status_text += f" | {step_info}"
        
        # Show agent status (always show in non-debug mode)
        from src.utils.debug_config import is_debug_mode
        if not is_debug_mode():
            self.logger.log(
                Panel(
                    status_text,
                    border_style=color,
                    padding=(0, 1)
                ),
                level=1
            )

    def show_progress_summary(self):
        """Show a summary of current progress"""
        if not self.step_durations:
            return
            
        total_time = sum(self.step_durations)
        avg_step_time = total_time / len(self.step_durations)
        
        # Create progress summary table
        table = Table(
            title="📊 Research Progress Summary", 
            show_header=True, 
            header_style="bold magenta",
            width=120
        )
        table.add_column("Metric", style="cyan", width=40)
        table.add_column("Value", style="yellow", width=80)
        
        table.add_row("Total Steps", str(len(self.step_durations)))
        table.add_row("Total Time", f"{total_time:.2f}s")
        table.add_row("Average Step Time", f"{avg_step_time:.2f}s")
        table.add_row("Input Tokens", f"{self.total_input_token_count:,}")
        table.add_row("Output Tokens", f"{self.total_output_token_count:,}")
        table.add_row("Total Tokens", f"{self.total_input_token_count + self.total_output_token_count:,}")
        
        if self.tool_usage:
            table.add_row("Tools Used", str(len(self.tool_usage)))
            for tool_name, usage in self.tool_usage.items():
                table.add_row(f"  └─ {tool_name}", f"{usage['calls']} calls ({usage['total_time']:.2f}s)")
        
        # Show progress summary (only in debug mode)
        from src.utils.debug_config import is_debug_mode
        if is_debug_mode():
            self.logger.log(table, level=1)

    def update_metrics(self, step_log):
        """Update the metrics of the monitor with enhanced UI.

        Args:
            step_log ([`MemoryStep`]): Step log to update the monitor with.
        """
        self.current_step += 1
        step_duration = step_log.timing.duration
        self.step_durations.append(step_duration)
        
        # Enhanced step information display
        step_info = f"Step {self.current_step}"
        if step_log.token_usage is not None:
            self.total_input_token_count += step_log.token_usage.input_tokens
            self.total_output_token_count += step_log.token_usage.output_tokens
            
            step_info += f" | ⏱️ {step_duration:.2f}s | 📝 {step_log.token_usage.input_tokens:,}→{step_log.token_usage.output_tokens:,} tokens"
        else:
            step_info += f" | ⏱️ {step_duration:.2f}s"
        
        # Show step completion with enhanced formatting (only in debug mode)
        from src.utils.debug_config import is_debug_mode
        if is_debug_mode():
            self.logger.log(
                Panel(
                    f"🎯 [bold green]Step {self.current_step} Completed[/bold green]\n"
                    f"⏱️  Duration: [bold cyan]{step_duration:.2f}s[/bold cyan]\n"
                    f"📊 Total Steps: [bold yellow]{len(self.step_durations)}[/bold yellow]",
                    border_style="green",
                    padding=(0, 1)
                ),
                level=1
            )
        
        # Show tool usage if any tools were called
        if hasattr(step_log, 'tool_calls') and step_log.tool_calls:
            tool_info = []
            for tool_call in step_log.tool_calls:
                tool_info.append(f"🛠️ {tool_call.name}")
            
            if tool_info:
                # Show tool usage (only in debug mode)
                from src.utils.debug_config import is_debug_mode
                if is_debug_mode():
                    self.logger.log(
                        Panel(
                            f"Tools Used in Step {self.current_step}:\n" + "\n".join(tool_info),
                            border_style="blue",
                            padding=(0, 1)
                        ),
                        level=1
                    )
        
        # Show progress summary every 5 steps
        if self.current_step % 5 == 0:
            self.show_progress_summary()