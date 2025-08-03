"""
Research Source Manager

This module manages the 3 core research data sources: Web, Vector Database, and MCP.
Users can select one, two, or all three sources for their research.
"""

import os
import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

# Import logger with fallback
try:
    from src.logger import logger
except ImportError:
    # Fallback for direct imports
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class SourceType(Enum):
    """Core research source types"""
    WEB = "web"
    VECTOR_DB = "vector_db"
    MCP = "mcp"


@dataclass
class SourceConfig:
    """Configuration for a research source"""
    name: str
    type: SourceType
    enabled: bool = True
    description: str = ""
    tools: List[str] = None
    agents: List[str] = None
    requirements: List[str] = None
    icon: str = "🔧"
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if self.agents is None:
            self.agents = []
        if self.requirements is None:
            self.requirements = []


class ResearchSourceManager:
    """
    Manages the 3 core research data sources and provides user-friendly selection interface.
    
    Sources:
    - Web Research: Internet search and information gathering
    - Vector Database: Local document search using embeddings
    - MCP Tools: Model Context Protocol integrations
    """
    
    def __init__(self, config_file: str = "research_sources.json"):
        self.config_file = config_file
        self.sources: Dict[str, SourceConfig] = {}
        self.selected_sources: Set[str] = set()
        self.user_preferences = {}
        
        self._initialize_core_sources()
        self._load_user_preferences()
    
    def _initialize_core_sources(self):
        """Initialize the 3 core research sources"""
        
        # Web Research Source
        self.sources["web"] = SourceConfig(
            name="🌐 Web Research",
            type=SourceType.WEB,
            description="Search the internet for current and comprehensive information",
            tools=["deep_researcher_tool", "auto_browser_use_tool"],
            agents=["deep_researcher_agent", "browser_use_agent"],
            requirements=["internet_connection"],
            icon="🌐"
        )
        
        # Vector Database Source
        self.sources["vector_db"] = SourceConfig(
            name="📚 Vector Database (Local Documents)",
            type=SourceType.VECTOR_DB,
            description="Search through your indexed local documents using semantic similarity",
            tools=["vector_search_tool", "vector_function_calls_tool"],
            agents=["vector_agent"],
            requirements=["vector_database"],
            icon="📚"
        )
        
        # MCP Tools Source
        self.sources["mcp"] = SourceConfig(
            name="🔧 MCP Tools",
            type=SourceType.MCP,
            description="Use Model Context Protocol tools for specialized data access",
            tools=[],  # MCP tools are loaded dynamically
            agents=[],
            requirements=["mcp_server"],
            icon="🔧"
        )
    
    def _load_user_preferences(self):
        """Load user preferences from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.user_preferences = data.get('preferences', {})
                    
                    # Load previously selected sources
                    saved_sources = data.get('selected_sources', [])
                    if saved_sources:
                        # Validate saved sources against current sources
                        valid_sources = [s for s in saved_sources if s in self.sources]
                        self.selected_sources = set(valid_sources)
                        from src.utils.debug_config import is_debug_mode
                        if is_debug_mode():
                            logger.info(f"Loaded {len(valid_sources)} saved research sources")
                    else:
                        self._set_default_selection()
            else:
                self._set_default_selection()
                
        except Exception as e:
            logger.warning(f"Could not load user preferences: {e}")
            self._set_default_selection()
    
    def _set_default_selection(self):
        """Set intelligent default source selection"""
        defaults = []
        
        # Always include web research as it's most universally available
        defaults.append("web")
        
        # Include vector database if it exists
        if self._is_source_available("vector_db"):
            defaults.append("vector_db")
        
        # Include MCP if available
        if self._is_source_available("mcp"):
            defaults.append("mcp")
        
        self.selected_sources = set(defaults)
        from src.utils.debug_config import is_debug_mode
        if is_debug_mode():
            logger.info(f"Set default research sources: {', '.join(defaults)}")
    
    def _save_user_preferences(self):
        """Save user preferences to config file"""
        try:
            data = {
                'preferences': self.user_preferences,
                'selected_sources': list(self.selected_sources),
                'last_updated': str(Path().resolve()),
                'version': '1.0'
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Saved user preferences with {len(self.selected_sources)} sources")
            
        except Exception as e:
            logger.warning(f"Could not save user preferences: {e}")
    
    def _is_source_available(self, source_id: str) -> bool:
        """Check if a research source is available and functional"""
        if source_id not in self.sources:
            return False
        
        source = self.sources[source_id]
        
        # Check requirements
        for requirement in source.requirements:
            if requirement == "vector_database":
                # Check if vector database exists
                if not os.path.exists("vector_db"):
                    return False
            elif requirement == "internet_connection":
                # Assume internet is available (could add actual check)
                pass
            elif requirement == "mcp_server":
                # Check if MCP server is configured
                # For now, assume it's available if config exists
                pass
        
        return True
    
    def get_available_sources(self) -> Dict[str, SourceConfig]:
        """Get all available research sources"""
        available = {}
        for source_id, source in self.sources.items():
            if self._is_source_available(source_id):
                available[source_id] = source
        return available
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all sources"""
        status = {}
        
        for source_id, source in self.sources.items():
            is_available = self._is_source_available(source_id)
            is_selected = source_id in self.selected_sources
            
            status[source_id] = {
                'name': source.name,
                'description': source.description,
                'icon': source.icon,
                'available': is_available,
                'selected': is_selected,
                'tools_count': len(source.tools),
                'agents_count': len(source.agents),
                'requirements': source.requirements,
                'status_emoji': "✅" if (is_available and is_selected) else "⚠️" if is_available else "❌"
            }
        
        return status
    
    def select_sources(self, source_ids: List[str]) -> bool:
        """Select specific research sources"""
        if not source_ids:
            logger.warning("No sources provided for selection")
            return False
        
        # Validate source IDs
        invalid_sources = [sid for sid in source_ids if sid not in self.sources]
        if invalid_sources:
            logger.error(f"Invalid source IDs: {invalid_sources}")
            return False
        
        # Check availability
        unavailable_sources = [sid for sid in source_ids if not self._is_source_available(sid)]
        if unavailable_sources:
            logger.warning(f"Unavailable sources will be skipped: {unavailable_sources}")
            source_ids = [sid for sid in source_ids if sid not in unavailable_sources]
        
        if not source_ids:
            logger.error("No valid and available sources to select")
            return False
        
        self.selected_sources = set(source_ids)
        self._save_user_preferences()
        
        logger.info(f"Selected {len(source_ids)} research sources: {', '.join(source_ids)}")
        return True
    
    def get_selected_sources(self) -> Dict[str, SourceConfig]:
        """Get currently selected research sources"""
        return {sid: self.sources[sid] for sid in self.selected_sources if sid in self.sources}
    
    def get_enabled_tools(self) -> List[str]:
        """Get list of tools for selected sources"""
        tools = ["planning_tool", "deep_analyzer_tool"]  # Always include core tools
        
        for source_id in self.selected_sources:
            if source_id in self.sources:
                tools.extend(self.sources[source_id].tools)
        
        return list(set(tools))  # Remove duplicates
    
    def get_enabled_agents(self) -> List[str]:
        """Get list of agents for selected sources"""
        agents = ["deep_analyzer_agent"]  # Always include core analysis agent
        
        for source_id in self.selected_sources:
            if source_id in self.sources:
                agents.extend(self.sources[source_id].agents)
        
        return list(set(agents))  # Remove duplicates
    
    def get_research_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive research capabilities based on selected sources"""
        selected = self.get_selected_sources()
        
        capabilities = {
            'sources_count': len(selected),
            'total_tools': len(self.get_enabled_tools()),
            'total_agents': len(self.get_enabled_agents()),
            'can_search_web': 'web' in self.selected_sources,
            'can_search_local': 'vector_db' in self.selected_sources,
            'can_use_mcp': 'mcp' in self.selected_sources,
            'has_parallel_processing': 'vector_db' in self.selected_sources and 'web' in self.selected_sources,
            'source_names': [s.name for s in selected.values()],
            'source_descriptions': [s.description for s in selected.values()]
        }
        
        return capabilities
    
    def create_dynamic_agent_config(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create dynamic agent configuration based on selected sources"""
        config = base_config.copy()
        
        # Update tools list
        config['tools'] = self.get_enabled_tools()
        
        # Update managed agents list if this is a planning agent
        if 'managed_agents' in config:
            config['managed_agents'] = self.get_enabled_agents()
        
        # Add source information
        config['research_sources'] = {
            'enabled_sources': list(self.selected_sources),
            'capabilities': self.get_research_capabilities()
        }
        
        return config
    
    def get_source_summary(self) -> str:
        """Get a human-readable summary of selected sources"""
        if not self.selected_sources:
            return "❌ No research sources selected"
        
        selected = self.get_selected_sources()
        capabilities = self.get_research_capabilities()
        
        summary_parts = [
            f"🎯 **Active Research Sources** ({len(selected)} enabled):",
            ""
        ]
        
        for source_id, source in selected.items():
            status_emoji = "✅" if self._is_source_available(source_id) else "⚠️"
            summary_parts.append(f"  {status_emoji} {source.name}")
            summary_parts.append(f"     └─ {source.description}")
        
        summary_parts.extend([
            "",
            f"⚡ **Research Capabilities**:",
            f"  • Tools Available: {capabilities['total_tools']}",
            f"  • Agents Available: {capabilities['total_agents']}",
            f"  • Web Search: {'✅' if capabilities['can_search_web'] else '❌'}",
            f"  • Local Search: {'✅' if capabilities['can_search_local'] else '❌'}",
            f"  • MCP Tools: {'✅' if capabilities['can_use_mcp'] else '❌'}",
            f"  • Parallel Processing: {'✅' if capabilities['has_parallel_processing'] else '❌'}"
        ])
        
        return "\n".join(summary_parts)


# Global instance
_source_manager = None

def get_research_source_manager() -> ResearchSourceManager:
    """Get or create global research source manager instance"""
    global _source_manager
    
    if _source_manager is None:
        _source_manager = ResearchSourceManager()
        from src.utils.debug_config import is_debug_mode
        if is_debug_mode():
            logger.info("Research source manager initialized")
    
    return _source_manager 