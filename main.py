import argparse
import os
import sys
import asyncio
import logging
import warnings
from pathlib import Path

from mmengine import DictAction
from rich.panel import Panel

# Import for GUI directory picker
try:
    import tkinter as tk
    from tkinter import filedialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

root = str(Path(__file__).resolve().parents[0])
sys.path.append(root)


from src.logger import logger
from src.config import config
from src.models import model_manager
from src.agent import create_agent

# Import for source selection
from src.ui.source_selector import get_user_research_sources, show_current_configuration
from src.research_source_manager import get_research_source_manager
from src.utils.debug_config import set_debug_mode, is_debug_mode

def parse_args():
    parser = argparse.ArgumentParser(description='main')
    parser.add_argument("--config", default=os.path.join(root, "configs", "config_main.py"), help="config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for verbose logging")

    parser.add_argument(
        '--cfg-options',
        nargs='+',
        action=DictAction,
        help='override some settings in the used config, the key-value pair '
        'in xxx=yyy format will be merged into config file. If the value to '
        'be overwritten is a list, it should be like key="[a,b]" or key=a,b '
        'It also allows nested list/tuple values, e.g. key="[(a,b),(c,d)]" '
        'Note that the quotation marks are necessary and that no white space '
        'is allowed.')
    args = parser.parse_args()
    return args


def select_directory_gui():
    """Open a GUI directory picker dialog"""
    if not GUI_AVAILABLE:
        return None
    
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.lift()      # Bring to front
    root.attributes('-topmost', True)  # Keep on top
    
    # Open directory selection dialog
    directory = filedialog.askdirectory(
        title="Select Directory to Index",
        mustexist=True
    )
    
    # Clean up
    root.destroy()
    
    return directory if directory else None


def get_startup_choice():
    """Get user choice for startup option with a beautiful terminal UI"""
    
    # ANSI color codes for beautiful UI
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        MAGENTA = '\033[95m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    
    def print_banner():
        # Big ASCII art title
        title_art = f"""
{Colors.CYAN}{Colors.BOLD}
██████╗ ███████╗███████╗██████╗     ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗███████╗██████╗ 
██╔══██╗██╔════╝██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗
██║  ██║█████╗  █████╗  ██████╔╝    ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║█████╗  ██████╔╝
██║  ██║██╔══╝  ██╔══╝  ██╔═══╝     ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║██╔══╝  ██╔══██╗
██████╔╝███████╗███████╗██║         ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║███████╗██║  ██║
╚═════╝ ╚══════╝╚══════╝╚═╝         ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝

    ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
                             A D V A N C E D   M U L T I   A G E N T   R E S E A R C H   S Y S T E M
    ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
{Colors.ENDC}"""
        
        # Welcome message
        welcome_msg = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════════════╗
║  Welcome! I'm a sophisticated multi-agent AI research system that performs  ║
║  comprehensive deep research across multiple data sources. I can help you   ║
║  with:                                                                       ║
║  • Searching and analyzing research papers                                   ║
║  • Deep web research and analysis                                           ║
║  • Summarizing complex topics                                               ║
║  • Planning and executing research tasks                                    ║
║  • Connecting to MCP servers for enhanced capabilities                      ║
║  • Integrating with vector databases for semantic search                    ║
║                                                                              ║
║  ⏱️  Research Time: Each search request typically takes 10-30 minutes       ║
║     as I perform thorough analysis across multiple sources and agents.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
        
        print(title_art)
        print(welcome_msg)
    
    def print_startup_options():
        options = f"""
{Colors.YELLOW}{Colors.BOLD}🚀 STARTUP OPTIONS:{Colors.ENDC}

{Colors.GREEN}{Colors.BOLD}1. 📊 Start Research{Colors.ENDC}
   Begin research immediately with available tools and knowledge base

{Colors.BLUE}{Colors.BOLD}2. 📁 Index Documents{Colors.ENDC}
   Index documents from a directory into vector database for enhanced research

{Colors.RED}{Colors.BOLD}3. 🚪 Exit{Colors.ENDC}
   Exit the application
"""
        print(options)
    
    def get_choice():
        # A prominent input section for choice selection
        width = 80
        header_text = "🎯 CHOOSE YOUR STARTUP OPTION"
        prompt_text = "Enter your choice (1-3):"
    
        # Calculate padding for center alignment inside the box
        header_padding = ' ' * (width - len(header_text) - 1)
        prompt_padding = ' ' * (width - len(prompt_text) - 1)
    
        # Build and print the styled input box
        print("\n")
        print(f"{Colors.MAGENTA}{Colors.BOLD}╔{'═' * width}╗{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}║ {Colors.YELLOW}{Colors.BOLD}{Colors.UNDERLINE}{header_text}{Colors.ENDC}{header_padding}║{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}║ {Colors.CYAN}{prompt_text}{prompt_padding}║{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}╚{'═' * width}╝{Colors.ENDC}")
        
        # Position the input cursor
        print(f" {Colors.GREEN}{Colors.BOLD}└──> {Colors.ENDC}", end="")
    
        choice = input().strip()
    
        if choice in ['3', 'exit', 'quit']:
            return '3'  # Return choice instead of exiting directly
    
        if choice not in ['1', '2']:
            print(f"\n{Colors.RED}❌ Please enter a valid choice (1-3).{Colors.ENDC}")
            return get_choice()
    
        return choice
    
    print_banner()
    
    
    # Import and create the agents table for startup display
    from src.agent.agent import create_comprehensive_system_overview
    from rich.console import Console
    from rich.table import Table
    console = Console()
    
    # Create a startup agents table (without requiring full agent creation)
    def create_startup_agents_table():
        """Create a table showing all available agents at startup."""
        table = Table(
            title="🤖 [bold cyan]Available Agents & Capabilities[/bold cyan]",
            title_style="bold cyan",
            border_style="cyan",
            show_header=True,
            header_style="bold white",
            show_lines=True
        )
        
        table.add_column("Agent", style="bold yellow")
        table.add_column("Type", style="bold blue")
        table.add_column("Model", style="bold magenta")
        table.add_column("Description", style="white")
        
        # Define all available agents
        agents = [
            ("🎯 Planning Agent", "Main", "gpt-4.1-mini", "Orchestrates research workflow"),
            ("🔍 Deep Researcher", "Specialized", "gpt-4.1-mini", "Comprehensive web research"),
            ("🧠 Deep Analyzer", "Specialized", "gpt-4.1-mini", "Methodical topic analysis"),
            ("🌐 Browser Agent", "Specialized", "gpt-4.1-mini", "Real-time web interaction"),
            ("📊 Vector Agent", "Specialized", "gpt-4.1-mini", "Vector database queries"),
            ("🎯 Scoping Agent", "Specialized", "gpt-4.1-mini", "Interactive task scoping"),
            ("🛠️  General Agent", "Utility", "gpt-4.1-mini", "Multi-purpose execution")
        ]
        
        for agent_name, agent_type, model, description in agents:
            table.add_row(agent_name, agent_type, model, description)
        
        return table
    
    try:
        startup_table = create_startup_agents_table()
        console.print(startup_table)
    except Exception as e:
        print(f"❌ Error displaying agents table: {e}")
    
    print_startup_options()
    
    choice = get_choice()
    
    # Confirm choice
    choice_names = {'1': 'Start Research', '2': 'Index Documents', '3': 'Exit'}
    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Selected:{Colors.ENDC}")
    print(f"{Colors.CYAN}└─ {choice_names[choice]}{Colors.ENDC}")
    
    if choice != '3':
        print(f"\n{Colors.YELLOW}🚀 Initializing...{Colors.ENDC}\n")
    
    return choice


async def handle_document_indexing():
    """Handle the document indexing process"""
    
    # ANSI color codes
    class Colors:
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        ENDC = '\033[0m'
    
    print(f"{Colors.CYAN}{Colors.BOLD}📁 Document Indexing Setup{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * 50}{Colors.ENDC}")
    
    # Get directory path using GUI or fallback to CLI
    directory_path = None
    
    if GUI_AVAILABLE:
        print(f"\n{Colors.YELLOW}🗂️  Opening directory selection dialog...{Colors.ENDC}")
        print(f"{Colors.CYAN}Please select the directory containing documents to index.{Colors.ENDC}")
        print(f"{Colors.CYAN}Supported file types: PDF, TXT, MD, CSV, XLSX, PPTX, DOCX, PY, JS, TS, HTML, CSS, JSON, XML, YAML{Colors.ENDC}")
        
        directory_path = select_directory_gui()
        
        if not directory_path:
            print(f"{Colors.RED}❌ No directory selected. Returning to main menu.{Colors.ENDC}")
            return False
            
    else:
        # Fallback to CLI input if GUI not available
        print(f"\n{Colors.YELLOW}⚠️  GUI not available, using command line input.{Colors.ENDC}")
        print(f"{Colors.YELLOW}Please enter the path to the directory you want to index:{Colors.ENDC}")
        print(f"{Colors.CYAN}Supported file types: PDF, TXT, MD, CSV, XLSX, PPTX, DOCX, PY, JS, TS, HTML, CSS, JSON, XML, YAML{Colors.ENDC}")
        
        directory_path = input(f"{Colors.GREEN}Directory path: {Colors.ENDC}").strip()
        
        if not directory_path:
            print(f"{Colors.RED}❌ No directory path provided. Returning to main menu.{Colors.ENDC}")
            return False
        
        # Expand user path for CLI input
        directory_path = os.path.expanduser(directory_path)
    
    # Validate directory
    if not os.path.exists(directory_path):
        print(f"{Colors.RED}❌ Directory does not exist: {directory_path}{Colors.ENDC}")
        return False
    
    if not os.path.isdir(directory_path):
        print(f"{Colors.RED}❌ Path is not a directory: {directory_path}{Colors.ENDC}")
        return False
    
    print(f"\n{Colors.GREEN}✅ Directory selected: {directory_path}{Colors.ENDC}")
    
    # Ask about force reindexing
    print(f"\n{Colors.YELLOW}Force re-indexing of all documents? (y/N):{Colors.ENDC}")
    force_reindex = input().strip().lower() in ['y', 'yes']
    
    try:
        # Import and use the vector indexer tool
        from src.tools.vector_database import VectorIndexerTool
        
        print(f"\n{Colors.CYAN}🔄 Starting document indexing...{Colors.ENDC}")
        
        # Initialize the indexer tool
        indexer = VectorIndexerTool()
        
        # Perform the indexing
        result = await indexer.forward(directory_path, force_reindex)
        
        if result.error:
            print(f"\n{Colors.RED}❌ Indexing failed: {result.error}{Colors.ENDC}")
            return False
        
        # Display results
        output = result.output
        if output['status'] == 'completed':
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Indexing Completed Successfully!{Colors.ENDC}")
            print(f"{Colors.GREEN}├─ Files processed: {output['files_processed']}{Colors.ENDC}")
            print(f"{Colors.GREEN}├─ Documents indexed: {output['documents_indexed']}{Colors.ENDC}")
            print(f"{Colors.GREEN}└─ Message: {output['message']}{Colors.ENDC}")
            
            if 'db_path' in output:
                print(f"{Colors.CYAN}📍 Vector database location: {output['db_path']}{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}❌ Indexing failed: {output.get('message', 'Unknown error')}{Colors.ENDC}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"\n{Colors.RED}❌ Required dependencies not installed:{Colors.ENDC}")
        print(f"{Colors.RED}   Please install: pip install langchain langchain-community langchain-openai langchain-chroma{Colors.ENDC}")
        print(f"{Colors.RED}   Error: {e}{Colors.ENDC}")
        return False
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error during indexing: {e}{Colors.ENDC}")
        return False


def get_user_task():
    """Get task from user with a beautiful terminal UI"""
    
    # ANSI color codes for beautiful UI
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        MAGENTA = '\033[95m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    
    def print_examples():
        examples = f"""
{Colors.YELLOW}{Colors.BOLD}💡 EXAMPLE RESEARCH TASKS:{Colors.ENDC}

{Colors.CYAN}• "Research the latest developments in quantum computing and summarize key findings"
• "Analyze the impact of AI on healthcare industry in 2024"
• "Investigate recent breakthroughs in renewable energy technology"
• "Research the current state of electric vehicle market and future trends"
• "Analyze the relationship between climate change and economic policy"
• "Research emerging trends in cybersecurity and digital threats"{Colors.ENDC}
"""
        print(examples)
    
    def get_input():
        # A more prominent and visually appealing input section
        width = 100  # Much larger width for bigger text
        header_text = "🎯 WHAT WOULD YOU LIKE ME TO RESEARCH TODAY?"
        prompt_text = "Enter your research task (or 'quit' to exit):"
    
        # Calculate padding for center alignment inside the box
        header_padding = ' ' * (width - len(header_text) - 1)
        prompt_padding = ' ' * (width - len(prompt_text) - 1)
    
        # Build and print the styled input box with much bigger, more prominent text
        print("\n")
        print(f"{Colors.MAGENTA}{Colors.BOLD}╔{'═' * width}╗{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}║ {Colors.YELLOW}{Colors.BOLD}{Colors.UNDERLINE}{header_text}{Colors.ENDC}{header_padding}║{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}║ {Colors.CYAN}{prompt_text}{prompt_padding}║{Colors.ENDC}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}╚{'═' * width}╝{Colors.ENDC}")
        
        # Position the input cursor
        print(f" {Colors.GREEN}{Colors.BOLD}└──> {Colors.ENDC}", end="")
    
        task = input().strip()
    
        if task.lower() in ['quit', 'exit', 'q']:
            print(f"\n{Colors.YELLOW}👋 Goodbye! Thanks for using Deep Research Agent.{Colors.ENDC}")
            sys.exit(0)
    
        if not task:
            print(f"\n{Colors.RED}❌ Please enter a valid task.{Colors.ENDC}")
            return get_input()
    
        return task
    
    print_examples()
    
    task = get_input()
    
    return task


async def main():
    # Parse command line arguments
    args = parse_args()
    
    # Set global debug flag
    set_debug_mode(args.debug)

    # Initialize the configuration
    config.init_config(args.config, args)

    # Initialize the logger with appropriate level based on debug mode
    # log_level = 2 if is_debug_mode() else 1  # DEBUG level for debug mode, INFO for normal mode
    # logger.init_logger(log_path=config.log_path, level=log_level)

    # Decide logging level based on debug mode
    if is_debug_mode():
        log_level = logging.DEBUG
        warning_filter = "default"  # show warnings in debug mode
    else:
        log_level = logging.ERROR
        warning_filter = "ignore"   # hide all warnings in non-debug mode

    # Initialize your logger
    logger.init_logger(log_path=config.log_path, level=log_level)

    # Set warnings filter accordingly
    warnings.simplefilter(warning_filter)
    
    # Show logger initialization message (only in debug mode)
    if is_debug_mode():
        logger.log(
            Panel(
                f"[bold green]✅ Logger initialized successfully[/bold green]\n"
                f"[dim]Log file: {config.log_path}[/dim]\n"
                f"[bold yellow]🔧 Debug mode enabled - verbose logging active[/bold yellow]",
                title="📝 [bold green]System Logger[/bold green]",
                border_style="green",
                padding=(0, 1)
            ),
            level=1
        )

    # Show configuration summary (only in debug mode)
    if is_debug_mode():
        logger.log(
            Panel(
                f"[bold cyan]📋 Configuration Loaded[/bold cyan]\n"
                f"[dim]Configuration details available in logs[/dim]",
                title="⚙️ [bold cyan]Configuration[/bold cyan]",
                border_style="cyan",
                padding=(0, 1)
            ),
            level=1
        )

    # Main application loop
    while True:
        # Get startup choice
        startup_choice = get_startup_choice()
        
        if startup_choice == '2':
            # Handle document indexing
            indexing_success = await handle_document_indexing()
            
            # Color codes for consistent UI
            class Colors:
                YELLOW = '\033[93m'
                GREEN = '\033[92m'
                RED = '\033[91m'
                CYAN = '\033[96m'
                BOLD = '\033[1m'
                ENDC = '\033[0m'
            
            # Show indexing summary and return to menu
            print(f"\n{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.CYAN}📊 INDEXING PROCESS SUMMARY{Colors.ENDC}")
            print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
            
            if indexing_success:
                print(f"{Colors.GREEN}✅ Status: Indexing completed successfully{Colors.ENDC}")
                print(f"{Colors.GREEN}🎉 Your documents have been indexed and are ready for research!{Colors.ENDC}")
            else:
                print(f"{Colors.RED}❌ Status: Indexing failed{Colors.ENDC}")
                print(f"{Colors.YELLOW}💡 You can try again or proceed with research using existing data{Colors.ENDC}")
            
            print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
            print(f"{Colors.YELLOW}🔄 Returning to main menu...{Colors.ENDC}")
            
            # Pause to let user see the summary
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
            continue  # Return to main menu
            
        elif startup_choice == '3':
            # Exit application
            print("\n👋 Goodbye! Thank you for using Deep Research Agent!")
            return
            
        # If startup_choice == '1' (Start Research), continue with research flow
        break
    
    # === NEW: RESEARCH SOURCE SELECTION ===
    print("\n" + "="*80)
    print("🎯 RESEARCH SOURCE CONFIGURATION")
    print("="*80)
    
    # Get research source selection from user
    source_selection_success = get_user_research_sources()
    
    if not source_selection_success:
        print("❌ Research source selection failed. Exiting...")
        return
    
    # Get the source manager to configure agents dynamically
    source_manager = get_research_source_manager()
    
    # === DYNAMIC AGENT CONFIGURATION ===
    # Update the configuration based on selected sources
    original_planning_config = config.planning_agent_config.copy()
    config.planning_agent_config = source_manager.create_dynamic_agent_config(config.planning_agent_config)
    
    # Update other agent configs if they exist
    if hasattr(config, 'deep_researcher_agent_config'):
        config.deep_researcher_agent_config = source_manager.create_dynamic_agent_config(config.deep_researcher_agent_config)
    
    if hasattr(config, 'deep_analyzer_agent_config'):
        config.deep_analyzer_agent_config = source_manager.create_dynamic_agent_config(config.deep_analyzer_agent_config)
    
    # Show final research configuration (only in debug mode)
    capabilities = source_manager.get_research_capabilities()
    if is_debug_mode():
        logger.log(
            Panel(
                f"[bold green]🎯 Research Sources Configured[/bold green]\n"
                f"[dim]Active sources: {capabilities['sources_count']} | "
                f"Tools: {capabilities['total_tools']} | "
                f"Agents: {capabilities['total_agents']}[/dim]\n\n"
                f"[yellow]📊 Capabilities:[/yellow]\n"
                f"• Web Research: {'✅' if capabilities['can_search_web'] else '❌'}\n"
                f"• Local Documents: {'✅' if capabilities['can_search_local'] else '❌'}\n"
                f"• MCP Tools: {'✅' if capabilities['can_use_mcp'] else '❌'}",
                title="🎯 [bold green]Research Configuration[/bold green]",
                border_style="green",
                padding=(0, 1)
            ),
            level=1
        )
    
    # Initialize models (only reached when starting research)
    if is_debug_mode():
        logger.log(
            Panel(
                "[bold yellow]🤖 Initializing AI Models[/bold yellow]\n"
                "[dim]Loading and configuring language models...[/dim]",
                title="🤖 [bold yellow]Model Initialization[/bold yellow]",
                border_style="yellow",
                padding=(0, 1)
            ),
            level=1
        )
    model_manager.init_models(use_local_proxy=False)
    
    # Show models summary (only in debug mode)
    if is_debug_mode():
        registered_models = list(model_manager.registed_models.keys())
        logger.log(
            Panel(
                f"[bold green]✅ Models initialized successfully[/bold green]\n"
                f"[dim]Available models: {', '.join(registered_models)}[/dim]",
                title="🤖 [bold green]Model Status[/bold green]",
                border_style="green",
                padding=(0, 1)
            ),
            level=1
        )

    # Create agent with dynamic configuration
    if is_debug_mode():
        logger.log(
            Panel(
                f"[bold magenta]🏗️  Building Agent System[/bold magenta]\n"
                f"[dim]Creating research agent network with {capabilities['sources_count']} data sources...[/dim]\n\n"
                f"[yellow]🔧 Agent Configuration:[/yellow]\n"
                f"• Planning Agent: {config.planning_agent_config.get('name', 'Planning Agent')}\n"
                f"• Enabled Tools: {len(source_manager.get_enabled_tools())}\n"
                f"• Managed Agents: {len(source_manager.get_enabled_agents())}\n"
                f"• Research Sources: {', '.join([s.name.split(' ')[0] for s in source_manager.get_selected_sources().values()])}",
                title="🏗️ [bold magenta]Agent Construction[/bold magenta]",
                border_style="magenta",
                padding=(0, 1)
            ),
            level=1
        )
    agent = await create_agent(config)
    
    # Show agent tree visualization (tools only)
    # logger.visualize_agent_tree(agent)

    task = get_user_task()
    
    # This is a placeholder for the color class since it's defined inside get_user_task
    class Colors:
        YELLOW = '\033[93m'
        ENDC = '\033[0m'
        GREEN = '\033[92m'
        BOLD = '\033[1m'
        CYAN = '\033[96m'

    print(f"\n{Colors.YELLOW}🚀 Starting research task...{Colors.ENDC}")
    
    # Show research summary before starting
    selected_sources = source_manager.get_selected_sources()
    print(f"{Colors.CYAN}📊 Research will use:{Colors.ENDC}")
    for source in selected_sources.values():
        print(f"  • {source.icon} {source.name}")
    print()
    
    res = await agent.run(task)
    
    # Show completion with beautiful UI
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Research Complete!{Colors.ENDC}")
    print(f"{Colors.CYAN}┌─ Final Result:{Colors.ENDC}")
    print(f"{Colors.CYAN}└─ {Colors.ENDC}{str(res)}")
    print(f"\n{Colors.YELLOW}✨ Thank you for using Deep Research Agent! 👋 Goodbye!{Colors.ENDC}")
    print()

if __name__ == '__main__':
    asyncio.run(main())