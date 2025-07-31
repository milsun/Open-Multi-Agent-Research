"""
Research Source Selection UI

This module provides a simple and intuitive interface for users to select
from the 3 core research data sources: Web, Vector Database, and MCP.
"""

import os
import sys
from typing import List, Dict, Set
from src.research_source_manager import get_research_source_manager, SourceConfig


class Colors:
    """ANSI color codes for beautiful terminal output"""
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


def print_section_header(title: str, subtitle: str = ""):
    """Print a beautiful section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"{'=' * 70}{Colors.ENDC}")


def print_source_card(source_id: str, source: SourceConfig, status: Dict, is_selected: bool, index: int):
    """Print a beautiful card for each research source"""
    # Status indicators
    available_indicator = status['status_emoji']
    selected_indicator = "✅" if is_selected else "⬜"
    
    # Color coding based on status
    if status['available'] and is_selected:
        color = Colors.GREEN
    elif status['available']:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    
    print(f"\n{color}{Colors.BOLD}[{index}] {selected_indicator} {source.name}{Colors.ENDC}")
    print(f"     {Colors.CYAN}└─ {source.description}{Colors.ENDC}")
    
    # Status details
    if not status['available'] and status['requirements']:
        req_text = ', '.join(status['requirements'])
        print(f"     {Colors.RED}└─ Missing: {req_text}{Colors.ENDC}")


def print_quick_options():
    """Print quick selection options"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}🚀 Quick Options:{Colors.ENDC}")
    print(f"  {Colors.CYAN}[A] All Available Sources{Colors.ENDC} - Use all sources that are available")
    print(f"  {Colors.CYAN}[W] Web Only{Colors.ENDC} - Internet research only")
    print(f"  {Colors.CYAN}[L] Local Only{Colors.ENDC} - Vector database and MCP only (no web)")


def show_current_configuration():
    """Display current research source configuration"""
    source_manager = get_research_source_manager()
    
    print_section_header("📊 CURRENT RESEARCH CONFIGURATION")
    
    # Get current status
    status = source_manager.get_source_status()
    selected_sources = source_manager.get_selected_sources()
    capabilities = source_manager.get_research_capabilities()
    
    if not selected_sources:
        print(f"{Colors.RED}{Colors.BOLD}❌ No research sources are currently selected!{Colors.ENDC}")
        print(f"{Colors.YELLOW}Please select at least one source to enable research functionality.{Colors.ENDC}")
        return False
    
    # Show selected sources
    print(f"{Colors.GREEN}{Colors.BOLD}✅ Active Sources ({len(selected_sources)}):{Colors.ENDC}")
    for source_id, source in selected_sources.items():
        source_status = status[source_id]
        print(f"  {source_status['status_emoji']} {source.name}")
        print(f"     └─ {Colors.CYAN}{source.description}{Colors.ENDC}")
    
    # Show capabilities summary
    print(f"\n{Colors.BLUE}{Colors.BOLD}⚡ Research Capabilities:{Colors.ENDC}")
    capability_items = [
        ("Web Research", capabilities['can_search_web']),
        ("Local Documents", capabilities['can_search_local']),
        ("MCP Tools", capabilities['can_use_mcp']),
    ]
    
    for name, enabled in capability_items:
        indicator = "✅" if enabled else "❌"
        color = Colors.GREEN if enabled else Colors.RED
        print(f"  {indicator} {color}{name}{Colors.ENDC}")
    
    return True


def select_research_sources(force_selection: bool = False) -> bool:
    """
    Interactive research source selection interface
    
    Args:
        force_selection: If True, forces user to select sources even if some are already selected
        
    Returns:
        bool: True if sources were selected successfully, False otherwise
    """
    source_manager = get_research_source_manager()
    
    # Show current configuration first
    has_selection = show_current_configuration()
    
    # If user already has sources and we're not forcing, ask if they want to change
    if has_selection and not force_selection:
        print(f"\n{Colors.YELLOW}You already have research sources configured.{Colors.ENDC}")
        change_choice = input(f"{Colors.CYAN}Would you like to change your source selection? (y/N): {Colors.ENDC}").lower().strip()
        
        if change_choice not in ['y', 'yes']:
            print(f"{Colors.GREEN}✅ Using existing research source configuration{Colors.ENDC}")
            return True
    
    print_section_header("🎯 RESEARCH SOURCE SELECTION", "Choose your data sources for research")
    
    # Get available sources and their status
    available_sources = source_manager.get_available_sources()
    all_sources = source_manager.sources
    status = source_manager.get_source_status()
    currently_selected = source_manager.selected_sources
    
    if not available_sources:
        print(f"{Colors.RED}{Colors.BOLD}❌ No research sources are available!{Colors.ENDC}")
        print(f"{Colors.YELLOW}Please ensure you have:")
        print(f"  • Internet connection for web research")
        print(f"  • Indexed documents for vector database search")
        print(f"  • Configured MCP tools if needed{Colors.ENDC}")
        return False
    
    # Display all 3 core sources
    print(f"{Colors.BLUE}{Colors.BOLD}📋 Available Research Sources:{Colors.ENDC}")
    
    source_order = ["web", "vector_db", "mcp"]  # Fixed order for the 3 core sources
    for i, source_id in enumerate(source_order, 1):
        if source_id in all_sources:
            source = all_sources[source_id]
            is_selected = source_id in currently_selected
            print_source_card(source_id, source, status[source_id], is_selected, i)
    
    # Show quick options
    print_quick_options()
    
    # Get user selection
    print(f"\n{Colors.BOLD}Selection Options:{Colors.ENDC}")
    print(f"  • Enter numbers (e.g., '1,2' or '1 2 3' for multiple sources)")
    print(f"  • Use quick options (A/W/L)")
    print(f"  • Enter 'current' to keep existing selection")
    
    while True:
        try:
            print(f"\n{Colors.CYAN}{Colors.BOLD}Research Sources Selection:{Colors.ENDC}")
            user_input = input(f"{Colors.YELLOW}Your choice: {Colors.ENDC}").strip()
            
            if not user_input:
                print(f"{Colors.RED}Please enter a selection{Colors.ENDC}")
                continue
            
            # Handle special commands
            if user_input.lower() == 'current':
                if currently_selected:
                    print(f"{Colors.GREEN}✅ Keeping current selection{Colors.ENDC}")
                    return True
                else:
                    print(f"{Colors.RED}No current selection exists{Colors.ENDC}")
                    continue
            
            # Handle quick options
            selected_ids = []
            if user_input.upper() == 'A':  # All available
                selected_ids = list(available_sources.keys())
                print(f"{Colors.GREEN}Selected: All available sources{Colors.ENDC}")
            elif user_input.upper() == 'W':  # Web only
                if 'web' in available_sources:
                    selected_ids = ['web']
                    print(f"{Colors.GREEN}Selected: Web research only{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Web research not available{Colors.ENDC}")
                    continue
            elif user_input.upper() == 'L':  # Local only
                local_sources = [sid for sid in available_sources.keys() 
                               if sid in ['vector_db', 'mcp']]
                if local_sources:
                    selected_ids = local_sources
                    print(f"{Colors.GREEN}Selected: Local sources only{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}No local sources available{Colors.ENDC}")
                    continue
            else:
                # Handle number selections
                try:
                    # Parse numbers (handle both comma and space separated)
                    numbers_str = user_input.replace(',', ' ')
                    numbers = [int(x.strip()) for x in numbers_str.split() if x.strip().isdigit()]
                    
                    if not numbers:
                        print(f"{Colors.RED}Please enter valid numbers or options (A/W/L){Colors.ENDC}")
                        continue
                    
                    # Validate numbers (1-3 for the 3 core sources)
                    invalid_numbers = [n for n in numbers if n < 1 or n > 3]
                    if invalid_numbers:
                        print(f"{Colors.RED}Invalid numbers: {invalid_numbers}. Please use 1-3{Colors.ENDC}")
                        continue
                    
                    # Map numbers to source IDs
                    number_to_source = {1: "web", 2: "vector_db", 3: "mcp"}
                    selected_ids = [number_to_source[n] for n in numbers]
                    
                    # Check if any selected sources are unavailable
                    unavailable = [sid for sid in selected_ids if sid not in available_sources]
                    if unavailable:
                        unavailable_names = [all_sources[sid].name for sid in unavailable]
                        print(f"{Colors.YELLOW}Warning: Some selected sources are unavailable:{Colors.ENDC}")
                        for name in unavailable_names:
                            print(f"  ❌ {name}")
                        selected_ids = [sid for sid in selected_ids if sid in available_sources]
                    
                    if not selected_ids:
                        print(f"{Colors.RED}No valid sources selected{Colors.ENDC}")
                        continue
                        
                except ValueError:
                    print(f"{Colors.RED}Invalid input. Please enter numbers (1-3) or options (A/W/L){Colors.ENDC}")
                    continue
            
            # Validate final selection
            if not selected_ids:
                print(f"{Colors.RED}No sources selected. Please choose at least one source.{Colors.ENDC}")
                continue
            
            # Show selection summary and confirm
            print(f"\n{Colors.BLUE}{Colors.BOLD}📋 Selection Summary:{Colors.ENDC}")
            for sid in selected_ids:
                source = all_sources[sid]
                print(f"  ✅ {source.name}")
                print(f"     └─ {Colors.CYAN}{source.description}{Colors.ENDC}")
            
            # Show capabilities this will enable
            temp_manager = get_research_source_manager()
            temp_manager.selected_sources = set(selected_ids)
            capabilities = temp_manager.get_research_capabilities()
            
            # Confirm selection
            confirm = input(f"\n{Colors.YELLOW}Confirm this selection? (Y/n): {Colors.ENDC}").lower().strip()
            
            if confirm in ['', 'y', 'yes']:
                # Apply selection
                success = source_manager.select_sources(selected_ids)
                
                if success:
                    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Research sources configured successfully!{Colors.ENDC}")
                    return True
                else:
                    print(f"{Colors.RED}❌ Failed to configure research sources{Colors.ENDC}")
                    return False
            else:
                print(f"{Colors.YELLOW}Selection cancelled. Please choose again.{Colors.ENDC}")
                continue
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Selection cancelled by user{Colors.ENDC}")
            return False
        except Exception as e:
            print(f"{Colors.RED}Error during selection: {e}{Colors.ENDC}")
            continue


def show_detailed_help():
    """Show detailed help information about the 3 core research sources"""
    print_section_header("📖 RESEARCH SOURCES HELP")
    
    help_content = [
        ("🌐 Web Research", 
         "Search the internet for current and comprehensive information. Includes web scraping, search APIs, and browser automation for interactive content."),
        
        ("📚 Vector Database (Local Documents)", 
         "Search through your indexed local documents using semantic similarity. Fast, private, and perfect for your personal knowledge base."),
        
        ("🔧 MCP Tools", 
         "Use Model Context Protocol tools for specialized data access. Enables integration with custom APIs, databases, and external systems."),
    ]
    
    for title, description in help_content:
        print(f"\n{Colors.BLUE}{Colors.BOLD}{title}:{Colors.ENDC}")
        print(f"  {Colors.CYAN}{description}{Colors.ENDC}")
    
    print(f"\n{Colors.YELLOW}{Colors.BOLD}💡 Selection Tips:{Colors.ENDC}")
    print(f"  • Select {Colors.CYAN}Web Only{Colors.ENDC} for current events and online research")
    print(f"  • Choose {Colors.CYAN}Local Only{Colors.ENDC} for private/sensitive research")
    print(f"  • Use {Colors.CYAN}All Sources{Colors.ENDC} for comprehensive research with maximum capabilities")
    print(f"  • You can combine any sources (e.g., Web + Vector DB for parallel processing)")


def get_user_research_sources() -> bool:
    """
    Main entry point for research source selection.
    Returns True if sources were successfully configured.
    """
    try:
        return select_research_sources()
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}❌ Error in source selection: {e}{Colors.ENDC}")
        return False


if __name__ == "__main__":
    # Demo/test the source selector
    print("🧪 Research Source Selector Demo (3 Core Sources)")
    success = get_user_research_sources()
    if success:
        print("✅ Demo completed successfully")
    else:
        print("❌ Demo failed")
        sys.exit(1) 