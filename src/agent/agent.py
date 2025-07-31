from typing import List, Dict, Any

from src.registry import AGENT, TOOL
from src.models import model_manager
from src.tools import make_tool_instance
from src.mcp.mcpadapt import MCPAdapt, AsyncToolAdapter
from src.logger import logger
from rich.panel import Panel
from rich.table import Table
from rich.console import Console


def create_system_status_table(main_agent, managed_agents: List = None, mcp_tools_count: int = 0) -> Table:
    """Create a comprehensive system status table showing all agents with details."""
    table = Table(
        title="🤖 [bold cyan]Agent System Status Dashboard[/bold cyan]",
        title_style="bold cyan",
        border_style="cyan",
        show_header=True,
        header_style="bold white",
        show_lines=True  # Add lines between rows for better readability
    )
    
    # Let columns auto-size based on content for proper rendering
    table.add_column("Agent Name", style="bold yellow")
    table.add_column("Type", style="bold blue")
    table.add_column("Status", style="bold green")
    table.add_column("LLM", style="bold magenta")
    table.add_column("Tools", style="white")
    table.add_column("Description", style="white")
    
    # Main Agent info
    main_agent_name = getattr(main_agent, 'name', main_agent.__class__.__name__)
    main_agent_description = getattr(main_agent, 'description', 'Main orchestrator agent')
    main_agent_model = getattr(main_agent.model, 'model_id', 'Unknown')
    main_agent_tools = list(main_agent.tools.keys()) if hasattr(main_agent, 'tools') else []
    
    # Show all tools
    main_agent_tools_str = ", ".join(main_agent_tools) if main_agent_tools else "None"
    
    table.add_row(
        f"🎯 {main_agent_name}",
        "Main",
        "✅ Ready",
        main_agent_model,
        main_agent_tools_str,
        main_agent_description
    )
    
    # Managed Agents info
    if managed_agents and len(managed_agents) > 0:
        for agent in managed_agents:
            agent_name = getattr(agent, 'name', agent.__class__.__name__)
            agent_description = getattr(agent, 'description', 'Specialized agent')
            agent_model = getattr(agent.model, 'model_id', 'Unknown')
            agent_tools = list(agent.tools.keys()) if hasattr(agent, 'tools') else []
            
            # Show all tools
            agent_tools_str = ", ".join(agent_tools) if agent_tools else "None"
            
            table.add_row(
                f"🤖 {agent_name}",
                "Worker",
                "✅ Active",
                agent_model,
                agent_tools_str,
                agent_description
            )
    
    # MCP Connection info (as a summary row)
    if mcp_tools_count > 0:
        table.add_row(
            "🔗 MCP Tools",
            "External",
            "✅ Connected",
            f"{mcp_tools_count} tools",
            "FastMCP 2.0",
            "External capabilities"
        )
    
    return table


def create_system_init_table(mcp_tools_count: int, system_type: str, managed_agents_list: List[str] = None) -> Table:
    """Create a system initialization status table."""
    table = Table(
        title="🚀 [bold white]System Initialization Status[/bold white]",
        title_style="bold white",
        border_style="white",
        show_header=True,
        header_style="bold white",
        show_lines=True
    )
    
    # Let columns auto-size
    table.add_column("Component", style="bold yellow")
    table.add_column("Status", style="bold green")
    table.add_column("Details", style="white")
    
    # MCP Connection
    table.add_row(
        "🔗 MCP Connection",
        "✅ Connected" if mcp_tools_count > 0 else "⚠️ None",
        f"FastMCP 2.0 ({mcp_tools_count} tools)"
    )
    
    # System Architecture
    table.add_row(
        "🏗️ System Architecture",
        "✅ Ready",
        system_type
    )
    
    # Managed Agents (if hierarchical)
    if managed_agents_list:
        managed_details = ", ".join(managed_agents_list)
        table.add_row(
            "🤖 Managed Agents",
            "✅ Active",
            managed_details
        )
    else:
        table.add_row(
            "🤖 Managed Agents",
            "⚠️ None",
            "Single agent system"
        )
    
    return table


def create_agent_detail_table(agent) -> Table:
    """Create a detailed table for individual agent information."""
    table = Table(
        title=f"🤖 [bold cyan]{getattr(agent, 'name', agent.__class__.__name__)}[/bold cyan]",
        title_style="bold cyan",
        border_style="cyan",
        show_header=True,
        header_style="bold white",
        show_lines=True
    )
    
    table.add_column("Property", style="bold yellow")
    table.add_column("Value", style="white")
    
    # Agent basic info
    agent_name = getattr(agent, 'name', agent.__class__.__name__)
    agent_type = getattr(agent, 'type', agent.__class__.__name__)
    agent_description = getattr(agent, 'description', 'No description available')
    agent_model = getattr(agent.model, 'model_id', 'Unknown')
    agent_max_steps = getattr(agent, 'max_steps', 'Not set')
    
    table.add_row("Agent Type", "BLAHH")
    table.add_row("Model", agent_model)
    table.add_row("Description", agent_description)
    table.add_row("Tools Count", str(len(agent.tools)) if hasattr(agent, 'tools') else "0")
    table.add_row("Managed Agents", "0")  # This would need to be calculated based on your structure
    
    return table


def create_tools_table(agent) -> Table:
    """Create a table showing available tools for an agent."""
    table = Table(
        title="🛠️ [bold white]Available Tools[/bold white]",
        title_style="bold white",
        border_style="white",
        show_header=True,
        header_style="bold white",
        show_lines=True
    )
    
    table.add_column("Tool Name", style="bold yellow")
    table.add_column("Description", style="white")
    
    if hasattr(agent, 'tools') and agent.tools:
        for tool_name, tool in agent.tools.items():
            tool_description = getattr(tool, 'description', 'No description available')
            # Handle long descriptions by wrapping them appropriately
            if len(tool_description) > 100:
                tool_description = tool_description[:97] + "..."
            
            table.add_row(tool_name, tool_description)
    else:
        table.add_row("No tools", "No tools available for this agent")
    
    return table


async def build_agent(config,
                      agent_config,
                      default_tools = None,
                      default_mcp_tools=None,
                      default_managed_agents=None,
                      mcp_tools_count=0):
    """
    Build an agent based on the provided configuration.

    Args:
        config (dict): Configuration dictionary containing tool and model settings.
        agent_config (dict): Configuration dictionary containing agent settings.

    Returns:
        Agent instance.
    """
    tools = []
    mcp_tools = []
    managed_agent_tools = []
    tools_list = []
    mcp_tools_list = []
    managed_agents_list = []

    # Build Tools
    if default_tools is None:
        pass  # No tools to initialize
    else:
        used_tools = agent_config.get("tools", [])
        for tool_name in used_tools:
            if tool_name not in default_tools:
                logger.warning(f"Tool '{tool_name}' is not registered. Skipping.")
            config_name = f"{tool_name}_config"  # e.g., "python_interpreter_tool" -> "python_interpreter_tool_config"
            if config_name in config:
                # If the tool has a specific config, use it
                tool_config = config[config_name]
            else:
                # Otherwise, use the default tool instance
                tool_config = dict(type=tool_name)
            tool = TOOL.build(tool_config)
            tools.append(tool)
        
        tools_list = [tool.name for tool in tools]

    # Build MCP Tools
    if default_mcp_tools is None:
        pass  # No MCP tools to initialize
    else:
        used_mcp_tools = agent_config.get("mcp_tools", [])
        for tools_name in used_mcp_tools:
            if tools_name not in default_mcp_tools:
                logger.warning(f"MCP tool '{tools_name}' is not available. Skipping.")
            else:
                mcp_tool = default_mcp_tools[tools_name]
                mcp_tools.append(mcp_tool)
        
        mcp_tools_list = [tool.name for tool in mcp_tools]

    # Load Managed Agents
    if default_managed_agents is None:
        pass  # No managed agents to initialize
    else:
        used_managed_agents = agent_config.get("managed_agents", [])
        for managed_agent in default_managed_agents:
            if managed_agent.name not in used_managed_agents:
                logger.warning(f"Managed agent '{managed_agent.name}' is not registered. Skipping.")
            else:
                managed_agent_tool = make_tool_instance(managed_agent)
                managed_agent_tools.append(managed_agent_tool)
        
        managed_agents_list = [agent.name for agent in managed_agent_tools]

    # Display comprehensive system status table
    # Note: This will be called after the agent is built, so we'll handle it in create_agent
    pass

    # Load Model
    model = model_manager.registed_models[agent_config["model_id"]]

    # Build Agent
    combined_tools = tools + mcp_tools + managed_agent_tools
    agent_config = dict(
        type=agent_config.type,
        config=agent_config,
        model=model,
        tools=combined_tools,
        max_steps=agent_config.max_steps,
        name=agent_config.name,
        description=agent_config.description,
        provide_run_summary=agent_config.provide_run_summary
    )
    agent = AGENT.build(agent_config)

    return agent


async def create_agent(config):

    # Load MCP tools only if MCP is enabled
    mcpadapt_tools = {}
    mcp_tools_count = 0
    
    # Check if MCP is enabled in research sources
    from src.research_source_manager import get_research_source_manager
    source_manager = get_research_source_manager()
    mcp_enabled = 'mcp' in source_manager.selected_sources
    
    if mcp_enabled:
        try:
            mcpadapt = MCPAdapt(config.mcp_tools_config, AsyncToolAdapter())
            mcpadapt_tools = await mcpadapt.tools()
            mcp_tools_count = len(mcpadapt_tools) if mcpadapt_tools else 0
        except Exception as e:
            from src.utils.debug_config import is_debug_mode
            if is_debug_mode():
                logger.warning(f"Failed to load MCP tools: {e}")
            mcpadapt_tools = {}
            mcp_tools_count = 0
    
    if config.use_hierarchical_agent:
        agent_config = config.agent_config
        managed_agents = []
        used_managed_agents = agent_config.get("managed_agents", [])
        
        for agent_name in used_managed_agents:
            if agent_name not in AGENT:
                logger.warning(f"Managed agent '{agent_name}' is not registered. Skipping.")
            else:
                managed_agent_config_name = f"{agent_name}_config"
                managed_agent_config = config.get(managed_agent_config_name, None)
                managed_agent = await build_agent(
                    config,
                    managed_agent_config,
                    default_tools=TOOL,
                    default_mcp_tools=mcpadapt_tools,
                    mcp_tools_count=mcp_tools_count
                )
                managed_agents.append(managed_agent)
        
        managed_agents_list = [agent.name for agent in managed_agents]
        
        # Build the main agent
        agent = await build_agent(
            config,
            agent_config,
            default_tools=TOOL,
            default_mcp_tools=mcpadapt_tools,
            default_managed_agents=managed_agents,
            mcp_tools_count=mcp_tools_count
        )



        return agent
    
    else:
        agent_config = config.agent_config

        # Build agent
        agent = await build_agent(config,
            agent_config,
            default_tools=TOOL,
            default_mcp_tools=mcpadapt_tools,
            mcp_tools_count=mcp_tools_count
        )



        return agent


def create_comprehensive_system_overview(config, main_agent, managed_agents: List = None, mcp_tools_count: int = 0) -> Table:
    """Create a comprehensive overview showing ALL available agents and tools in the system."""
    from src.registry import AGENT, TOOL
    
    table = Table(
        title="🤖 [bold cyan]Complete System Overview - All Available Agents & Tools[/bold cyan]",
        title_style="bold cyan",
        border_style="cyan",
        show_header=True,
        header_style="bold white",
        show_lines=True
    )
    
    table.add_column("Component", style="bold yellow")
    table.add_column("Type", style="bold blue")
    table.add_column("Status", style="bold")
    table.add_column("Model/Config", style="bold magenta")
    table.add_column("Capabilities", style="white")
    table.add_column("Description", style="white")
    
    # Currently Active Main Agent
    main_agent_name = getattr(main_agent, 'name', main_agent.__class__.__name__)
    main_agent_description = getattr(main_agent, 'description', 'Main orchestrator agent')
    main_agent_model = getattr(main_agent.model, 'model_id', 'Unknown')
    main_agent_tools = list(main_agent.tools.keys()) if hasattr(main_agent, 'tools') else []
    
    table.add_row(
        f"🎯 {main_agent_name}",
        "Main Agent",
        "[green]✅ ACTIVE[/green]",
        main_agent_model,
        f"{len(main_agent_tools)} tools",
        main_agent_description
    )
    
    # Currently Active Managed Agents
    if managed_agents and len(managed_agents) > 0:
        for agent in managed_agents:
            agent_name = getattr(agent, 'name', agent.__class__.__name__)
            agent_description = getattr(agent, 'description', 'Specialized agent')
            agent_model = getattr(agent.model, 'model_id', 'Unknown')
            agent_tools = list(agent.tools.keys()) if hasattr(agent, 'tools') else []
            
            table.add_row(
                f"🤖 {agent_name}",
                "Managed Agent",
                "[green]✅ ACTIVE[/green]",
                agent_model,
                f"{len(agent_tools)} tools",
                agent_description
            )
    
    # All Available Agents in Config (including inactive ones)
    available_agent_configs = [
        ("scoping_agent", "Interactive scoping with clarification"),
        ("planning_agent", "Strategic task coordination"),
        ("vector_agent", "Vector database semantic search"),
        ("deep_researcher_agent", "Comprehensive web research"),
        ("deep_analyzer_agent", "Methodical problem analysis"),
        ("browser_use_agent", "Interactive web browsing"),
        ("general_agent", "General purpose task execution")
    ]
    
    active_agent_names = set([main_agent_name] + [getattr(a, 'name', '') for a in (managed_agents or [])])
    
    for agent_type, description in available_agent_configs:
        if agent_type not in active_agent_names:
            # Check if config exists
            config_name = f"{agent_type}_config"
            has_config = hasattr(config, config_name)
            
            if has_config:
                status = "[yellow]⚠️ AVAILABLE[/yellow]"
                status_desc = "Configured but not active"
            else:
                status = "[red]❌ UNAVAILABLE[/red]"
                status_desc = "Missing dependencies"
            
            table.add_row(
                f"🔧 {agent_type}",
                "Available Agent",
                status,
                "gpt-4.1-mini",
                status_desc,
                description
            )
        
    # All Available Tools
    registered_tools = [
        ("interactive_planning_tool", "Research plan presentation & confirmation"),
        ("user_clarification_tool", "Interactive user clarification"),
        ("planning_tool", "Task planning & management"),
        ("vector_search_tool", "Semantic document search"),
        ("vector_function_calls_tool", "Advanced vector operations"),
        ("deep_researcher_tool", "Web research & analysis"),
        ("deep_analyzer_tool", "Systematic problem analysis"),
        ("auto_browser_use_tool", "Automated web browsing"),
        ("web_searcher_tool", "General web search"),
        ("archive_searcher_tool", "Archive & historical search"),
        ("final_answer_tool", "Result finalization")
    ]
    
    # Get currently active tools
    active_tools = set(main_agent_tools)
    if managed_agents:
        for agent in managed_agents:
            if hasattr(agent, 'tools'):
                active_tools.update(agent.tools.keys())
    
    for tool_name, description in registered_tools:
        if tool_name in active_tools:
            status = "[green]✅ ACTIVE[/green]"
            capabilities = "Fully operational"
        else:
            # Check if tool is registered
            try:
                if tool_name in TOOL._module_dict:
                    status = "[yellow]⚠️ AVAILABLE[/yellow]"
                    capabilities = "Ready but not loaded"
                else:
                    status = "[red]❌ UNAVAILABLE[/red]"
                    capabilities = "Missing dependencies"
            except:
                status = "[red]❌ UNAVAILABLE[/red]"
                capabilities = "Missing dependencies"
        
        table.add_row(
            f"🛠️ {tool_name}",
            "Tool",
            status,
            "N/A",
            capabilities,
            description
        )
    
    # MCP Tools
    if mcp_tools_count > 0:
        table.add_row(
            "🔗 MCP Integration",
            "External",
            "[green]✅ CONNECTED[/green]",
            "FastMCP 2.0",
            f"{mcp_tools_count} external tools",
            "External system capabilities"
        )

    return table