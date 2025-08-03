import logging
import json
from enum import IntEnum
from typing import List, Optional

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from src.utils import (
    escape_code_brackets,
    Singleton
)

YELLOW_HEX = "#d4b702"

class LogLevel(IntEnum):
    OFF = -1  # No output
    ERROR = 0  # Only errors
    INFO = 1  # Normal output (default)
    DEBUG = 2  # Detailed output

class AgentLogger(logging.Logger, metaclass=Singleton):
    def __init__(self, name="logger", level=logging.INFO):
        # Initialize the parent class
        super().__init__(name, level)

        # Define a formatter for log messages
        self.formatter = logging.Formatter(
            fmt="\033[92m%(asctime)s - %(name)s:%(levelname)s\033[0m: %(filename)s:%(lineno)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    def init_logger(self, log_path: str, level=logging.INFO):
        """
        Initialize the logger with a file path and optional main process check.

        Args:
            log_path (str): The log file path.
            level (int, optional): The logging level. Defaults to logging.INFO.
            accelerator (Accelerator, optional): Accelerator instance to determine the main process.
        """

        # Add a console handler for logging to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(self.formatter)
        self.addHandler(console_handler)

        # Add a file handler for logging to the file
        file_handler = logging.FileHandler(
            log_path, mode="a"
        )  # 'a' mode appends to the file
        file_handler.setLevel(level)
        file_handler.setFormatter(self.formatter)
        self.addHandler(file_handler)

        self.console = Console(width=100)
        self.file_console = Console(file=open(log_path, "a"), width=100)

        # Prevent duplicate logs from propagating to the root logger
        self.propagate = False

    def log(self, *args, level: int | str | LogLevel = LogLevel.INFO, **kwargs) -> None:
        """Logs a message to the console.

        Args:
            level (LogLevel, optional): Defaults to LogLevel.INFO.
        """
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        if level <= self.level:
            self.info(*args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Overridden info method with stacklevel adjustment for correct log location.
        """
        if isinstance(msg, (Rule, Panel, Group, Tree, Table, Syntax)):
            self.console.print(msg)
            self.file_console.print(msg)
        else:
            kwargs.setdefault(
                "stacklevel", 2
            )  # Adjust stack level to show the actual caller
            if "style" in kwargs:
                kwargs.pop("style")
            if "level" in kwargs:
                kwargs.pop("level")
            super().info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        kwargs.setdefault("stacklevel", 2)
        super().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        kwargs.setdefault("stacklevel", 2)
        super().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        kwargs.setdefault("stacklevel", 2)
        super().critical(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        kwargs.setdefault("stacklevel", 2)
        super().debug(msg, *args, **kwargs)

    def log_error(self, error_message: str) -> None:
        self.info(escape_code_brackets(error_message), style="bold red", level=LogLevel.ERROR)

    def log_markdown(self, content: str, title: str | None = None, level=LogLevel.INFO, style=YELLOW_HEX) -> None:
        markdown_content = Syntax(
            content,
            lexer="markdown",
            theme="github-dark",
            word_wrap=True,
        )
        if title:
            self.info(
                Group(
                    Rule(
                        "[bold italic]" + title,
                        align="left",
                        style=style,
                    ),
                    markdown_content,
                ),
                level=level,
            )
        else:
            self.info(markdown_content, level=level)

    def log_code(self, title: str, content: str, level: int = LogLevel.INFO) -> None:
        self.info(
            Panel(
                Syntax(
                    content,
                    lexer="python",
                    theme="monokai",
                    word_wrap=True,
                ),
                title="[bold]" + title,
                title_align="left",
                box=box.HORIZONTALS,
            ),
            level=level,
        )

    def log_rule(self, title: str, level: int = LogLevel.INFO) -> None:
        self.info(
            Rule(
                "[bold]" + title,
                characters="━",
                style=YELLOW_HEX,
            ),
            level=LogLevel.INFO,
        )

    def log_task(self, content: str, subtitle: str, title: str | None = None, level: LogLevel = LogLevel.INFO) -> None:
        self.info(
            Panel(
                f"\n[bold]{escape_code_brackets(content)}\n",
                title="[bold]New run" + (f" - {title}" if title else ""),
                subtitle=subtitle,
                border_style=YELLOW_HEX,
                subtitle_align="left",
            ),
            level=level,
        )

    def log_messages(self, messages: list[dict], level: LogLevel = LogLevel.DEBUG) -> None:
        messages_as_string = "\n".join([json.dumps(dict(message), indent=4, ensure_ascii=False) for message in messages])
        self.info(
            Syntax(
                messages_as_string,
                lexer="markdown",
                theme="github-dark",
                word_wrap=True,
            ),
            level=level,
        )

    def visualize_agent_tree(self, agent):
        """Create a beautiful, modern visualization of the agent tree."""
        
        def create_tools_section(tools_dict):
            if not tools_dict:
                return Panel(
                    "[dim]No tools available[/dim]",
                    title="🛠️ [bold cyan]Available Tools[/bold cyan]",
                    border_style="cyan",
                    padding=(0, 1)
                )
            
            # Create a modern table for tools
            table = Table(
                show_header=True, 
                header_style="bold cyan",
                border_style="cyan",
                title="🛠️ [bold cyan]Available Tools[/bold cyan]",
                title_style="bold cyan",
                width=140
            )
            table.add_column("Tool Name", style="bold yellow", width=40)
            table.add_column("Description", style="white", width=100)

            for name, tool in tools_dict.items():
                # Get tool description
                description = getattr(tool, "description", str(tool))
                if len(description) > 120:
                    description = description[:117] + "..."
                
                table.add_row(name, description)

            return table

        def create_agent_info_panel(agent_obj, name: str = None):
            """Create a beautiful panel for agent information."""
            agent_name = name or agent_obj.__class__.__name__
            model_id = getattr(agent_obj.model, 'model_id', 'Unknown Model')
            description = getattr(agent_obj, 'description', 'No description available')
            
            # Create agent info panel
            info_panel = Panel(
                f"[bold cyan]Agent Type:[/bold cyan] [bold yellow]{agent_name}[/bold yellow]\n"
                f"[bold cyan]Model:[/bold cyan] [bold green]{model_id}[/bold green]\n"
                f"[bold cyan]Description:[/bold cyan] [white]{description}[/white]\n"
                f"[bold cyan]Tools Count:[/bold cyan] [bold magenta]{len(agent_obj.tools)}[/bold magenta]\n"
                f"[bold cyan]Managed Agents:[/bold cyan] [bold magenta]{len(agent_obj.managed_agents) if hasattr(agent_obj, 'managed_agents') else 0}[/bold magenta]",
                title=f"🤖 [bold blue]{agent_name}[/bold blue]",
                border_style="blue",
                padding=(1, 2),
                title_align="left"
            )
            return info_panel

        def build_agent_tree(parent_tree, agent_obj, agent_name: str = None):
            """Recursively builds the agent tree with enhanced styling."""
            
            # # Add tools section only
            # tools_section = create_tools_section(agent_obj.tools)
            # parent_tree.add(tools_section)

            # Add managed agents if any
            if hasattr(agent_obj, 'managed_agents') and agent_obj.managed_agents:
                managed_agents_panel = Panel(
                    f"[bold magenta]Total Managed Agents: {len(agent_obj.managed_agents)}[/bold magenta]",
                    title="🤖 [bold magenta]Managed Agents[/bold magenta]",
                    border_style="magenta",
                    padding=(0, 1)
                )
                parent_tree.add(managed_agents_panel)
                
                for name, managed_agent in agent_obj.managed_agents.items():
                    # Create a sub-tree for each managed agent
                    managed_agent_tree = parent_tree.add(f"🔄 [bold green]{name}[/bold green]")
                    build_agent_tree(managed_agent_tree, managed_agent, name)

        # Create main tree with enhanced styling
        main_agent_name = getattr(agent, 'name', agent.__class__.__name__)
        main_tree = Tree(
            f"🎯 [bold white]{main_agent_name}[/bold white]",
            guide_style="bright_blue"
        )
        
        # Build and print the agent tree (tools only)
        build_agent_tree(main_tree, agent, main_agent_name)
        self.console.print(main_tree)

logger = AgentLogger()